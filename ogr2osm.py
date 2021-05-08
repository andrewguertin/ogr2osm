#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' ogr2osm beta

This program takes any vector data understadable by OGR and outputs an OSM file
with that data.

By default tags will be naively copied from the input data. Hooks are provided
so that, with a little python programming, you can translate the tags however
you like. More hooks are provided so you can filter or even modify the features
themselves.

To use the hooks, create a file in the translations/ directory called myfile.py
and run ogr2osm.py -t myfile. This file should define a function with the name
of each hook you want to use. For an example, see the uvmtrans.py file.

The program will use projection metadata from the source, if it has any. If
there is no projection information, or if you want to override it, you can use
-e or -p to specify an EPSG code or Proj.4 string, respectively. If there is no
projection metadata and you do not specify one, EPSG:4326 will be used (WGS84
latitude-longitude)

For additional usage information, run ogr2osm.py --help

Copyright (c) 2012-2013 Paul Norman <penorman@mac.com>, Sebastiaan Couwenberg
<sebastic@xs4all.nl>, The University of Vermont <andrew.guertin@uvm.edu>

Released under the MIT license, as given in the file LICENSE, which must
accompany any distribution of this code.

Based very heavily on code released under the following terms:

(c) Iván Sánchez Ortega, 2009
<ivan@sanchezortega.es>
###############################################################################
#  "THE BEER-WARE LICENSE":                                                   #
#  <ivan@sanchezortega.es> wrote this file. As long as you retain this notice #
#  you can do whatever you want with this stuff. If we meet some day, and you #
#  think this stuff is worth it, you can buy me a beer in return.             #
###############################################################################

'''


import sys
import os
import optparse
import re

from osgeo import ogr
from osgeo import osr
from geom import *

from datetime import datetime

# import logging and set logging level to DEBUG
import logging as l
l.basicConfig(level=l.DEBUG, format="%(message)s")

# Determine major Python version is 2 or 3
IS_PYTHON2 = sys.version_info < (3, 0)

'''

See http://lxml.de/tutorial.html for the source of the includes

lxml should be the fastest method

'''

try:
    from lxml import etree
    l.debug("running with lxml.etree")
except ImportError:
    try:
        # Python 2.5
        import xml.etree.ElementTree as etree
        l.debug("running with ElementTree on Python 2.5+")
    except ImportError:
        try:
            # normal cElementTree install
            import cElementTree as etree
            l.debug("running with cElementTree")
        except ImportError:
            try:
                # normal ElementTree install
                import elementtree.ElementTree as etree
                l.debug("running with ElementTree")
            except ImportError:
                l.error("Failed to import ElementTree from any known place")
                raise


# Initialize
UNIQUE_NODE_INDEX = {}


def openData(source):
    if re.match('^PG:', source):
        return openDatabaseSource(source)
    else:
        return getFileData(source)


def openDatabaseSource(source):
    dataSource = ogr.Open(source, 0)  # 0 means read-only
    if dataSource is None:
        l.error('OGR failed to open connection to' + source)
        sys.exit(1)
    else:
        return dataSource


def getFileData(filename):
    ogr_accessmethods = [ "/vsicurl/", "/vsicurl_streaming/", "/vsisubfile/",
        "/vsistdin/" ]
    ogr_filemethods = [ "/vsisparse/", "/vsigzip/", "/vsitar/", "/vsizip/" ]
    ogr_unsupported = [ "/vsimem/", "/vsistdout/", ]
    has_unsup = [ m for m in ogr_unsupported if m[1:-1] in filename.split('/') ]
    if has_unsup:
        parser.error("Unsupported OGR access method(s) found: %s."
            % str(has_unsup)[1:-1])
    if not any([ m[1:-1] in filename.split('/') for m in ogr_accessmethods ]):
        # Not using any ogr_accessmethods
        real_filename = filename
        for fm in ogr_filemethods:
            if filename.find(fm) == 0:
                real_filename = filename[len(fm):]
                break
        if not os.path.exists(real_filename):
            parser.error("the file '%s' does not exist" % (real_filename))
        if len(filename) == len(real_filename):
            if filename.endswith('.gz'):
                filename = '/vsigzip/' + filename
            elif filename.endswith('.tar') or filename.endswith('.tgz') or \
              filename.endswith('.tar.gz'):
                filename = '/vsitar/' + filename
            elif filename.endswith('.zip'):
                filename = '/vsizip/' + filename

    fileDataSource = ogr.Open(filename, 0)  # 0 means read-only
    if fileDataSource is None:
        l.error('OGR failed to open ' + filename + ', format may be unsupported')
        sys.exit(1)
    if OPTIONS.noMemoryCopy:
        return fileDataSource
    else:
        memoryDataSource = ogr.GetDriverByName('Memory').CopyDataSource(fileDataSource,'memoryCopy')
        return memoryDataSource


def parseData(dataSource):
    l.debug("Parsing data")
    global TRANSLATIONS
    if OPTIONS.sqlQuery:
        layer = dataSource.ExecuteSQL(OPTIONS.sqlQuery)
        layer.ResetReading()
        parseLayer(TRANSLATIONS.filterLayer(layer))
    else:
        for i in range(dataSource.GetLayerCount()):
            layer = dataSource.GetLayer(i)
            layer.ResetReading()
            parseLayer(TRANSLATIONS.filterLayer(layer))


def getTransform(layer):
    global OPTIONS
    # First check if the user supplied a projection, then check the layer,
    # then fall back to a default
    spatialRef = None
    if OPTIONS.sourcePROJ4:
        spatialRef = osr.SpatialReference()
        spatialRef.ImportFromProj4(OPTIONS.sourcePROJ4)
    elif OPTIONS.sourceEPSG:
        spatialRef = osr.SpatialReference()
        spatialRef.ImportFromEPSG(OPTIONS.sourceEPSG)
    else:
        spatialRef = layer.GetSpatialRef()
        if spatialRef != None:
            l.info("Detected projection metadata:\n" + str(spatialRef))
        else:
            l.info("No projection metadata, falling back to EPSG:4326")

    if spatialRef == None:
        # No source proj specified yet? Then default to do no reprojection.
        # Some python magic: skip reprojection altogether by using a dummy
        # lamdba funcion. Otherwise, the lambda will be a call to the OGR
        # reprojection stuff.
        reproject = lambda geometry: None
    else:
        destSpatialRef = osr.SpatialReference()
        try:
            destSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        except AttributeError:
            pass
        # Destionation projection will *always* be EPSG:4326, WGS84 lat-lon
        destSpatialRef.ImportFromEPSG(4326)
        coordTrans = osr.CoordinateTransformation(spatialRef, destSpatialRef)
        reproject = lambda geometry: geometry.Transform(coordTrans)

    return reproject


def getLayerFields(layer):
    featureDefinition = layer.GetLayerDefn()
    fieldNames = []
    fieldCount = featureDefinition.GetFieldCount()
    for j in range(fieldCount):
        fieldNames.append(featureDefinition.GetFieldDefn(j).GetNameRef())
    return fieldNames


def getFeatureTags(ogrfeature, fieldNames):
    '''
    This function builds up a dictionary with the source data attributes and passes them to the filterTags function, returning the result.
    '''
    tags = {}
    for i in range(len(fieldNames)):
        # The field needs to be put into the appropriate encoding and leading or trailing spaces stripped
        if IS_PYTHON2:
            tags[fieldNames[i].decode(OPTIONS.encoding)] = ogrfeature.GetFieldAsString(i).decode(OPTIONS.encoding).strip()
        else:
            tags[fieldNames[i]] = ogrfeature.GetFieldAsString(i).strip()
    return TRANSLATIONS.filterTags(tags)


def parseLayer(layer):
    if layer is None:
        return
    fieldNames = getLayerFields(layer)
    reproject = getTransform(layer)

    for j in range(layer.GetFeatureCount()):
        ogrfeature = layer.GetNextFeature()
        parseFeature(TRANSLATIONS.filterFeature(ogrfeature, fieldNames, reproject), fieldNames, reproject)


def parseFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        return

    ogrgeometry = ogrfeature.GetGeometryRef()
    if ogrgeometry is None:
        return
    reproject(ogrgeometry)
    geometries = parseGeometry([ogrgeometry])

    for geometry in geometries:
        if geometry is None:
            return

        feature = Feature()
        feature.tags = getFeatureTags(ogrfeature, fieldNames)
        feature.geometry = geometry
        geometry.addparent(feature)

        TRANSLATIONS.filterFeaturePost(feature, ogrfeature, ogrgeometry)


def parseGeometry(ogrgeometries):
    returngeometries = []
    for ogrgeometry in ogrgeometries:
        geometryType = ogrgeometry.GetGeometryType()

        if (geometryType == ogr.wkbPoint or
            geometryType == ogr.wkbPoint25D):
            returngeometries.append(parsePoint(ogrgeometry))
        elif (geometryType == ogr.wkbLineString or
              geometryType == ogr.wkbLinearRing or
              geometryType == ogr.wkbLineString25D):
#             geometryType == ogr.wkbLinearRing25D does not exist
            returngeometries.append(parseLineString(ogrgeometry))
        elif (geometryType == ogr.wkbPolygon or
              geometryType == ogr.wkbPolygon25D):
            returngeometries.append(parsePolygon(ogrgeometry))
        elif (geometryType == ogr.wkbMultiPoint or
              geometryType == ogr.wkbMultiLineString or
              geometryType == ogr.wkbMultiPolygon or
              geometryType == ogr.wkbGeometryCollection or
              geometryType == ogr.wkbMultiPoint25D or
              geometryType == ogr.wkbMultiLineString25D or
              geometryType == ogr.wkbMultiPolygon25D or
              geometryType == ogr.wkbGeometryCollection25D):
            returngeometries.extend(parseCollection(ogrgeometry))
        else:
            l.warning("unhandled geometry, type: " + str(geometryType))
            returngeometries.append(None)

    return returngeometries


def addPoint(x, y):
    global UNIQUE_NODE_INDEX
    rx = int(round(x * 10**OPTIONS.roundingDigits))
    ry = int(round(y * 10**OPTIONS.roundingDigits))
    if (rx, ry) in UNIQUE_NODE_INDEX:
        return Geometry.geometries[UNIQUE_NODE_INDEX[(rx, ry)]]
    else:
        UNIQUE_NODE_INDEX[(rx, ry)] = len(Geometry.geometries)
        point = Point(int(round(x*10**OPTIONS.significantDigits)), int(round(y*10**OPTIONS.significantDigits)))
        return point


def parsePoint(ogrgeometry):
    return addPoint(ogrgeometry.GetX(), ogrgeometry.GetY())


def parseLineString(ogrgeometry):
    geometry = Way()
    # LineString.GetPoint() returns a tuple, so we can't call parsePoint on it
    # and instead have to create the point ourself
    for i in range(ogrgeometry.GetPointCount()):
        (x, y, unused) = ogrgeometry.GetPoint(i)
        mypoint = addPoint(x, y)
        geometry.points.append(mypoint)
        mypoint.addparent(geometry)
    return geometry


def parsePolygon(ogrgeometry):
    # Special case polygons with only one ring. This does not (or at least
    # should not) change behavior when simplify relations is turned on.
    if ogrgeometry.GetGeometryCount() == 0:
        l.warning("Polygon with no rings?")
    elif ogrgeometry.GetGeometryCount() == 1:
        result = parseLineString(ogrgeometry.GetGeometryRef(0))
        if len(result.points) > OPTIONS.maxNodesPerWay:
            global LONG_WAYS_FROM_POLYGONS
            LONG_WAYS_FROM_POLYGONS.add(result)
        return result
    else:
        geometry = Relation()
        try:
            exterior = parseLineString(ogrgeometry.GetGeometryRef(0))
            exterior.addparent(geometry)
        except:
            l.warning("Polygon with no exterior ring?")
            return None
        geometry.members.append((exterior, "outer"))
        for i in range(1, ogrgeometry.GetGeometryCount()):
            interior = parseLineString(ogrgeometry.GetGeometryRef(i))
            interior.addparent(geometry)
            geometry.members.append((interior, "inner"))
        return geometry


def parseCollection(ogrgeometry):
    # OGR MultiPolygon maps easily to osm multipolygon, so special case it
    # TODO: Does anything else need special casing?
    geometryType = ogrgeometry.GetGeometryType()
    if (geometryType == ogr.wkbMultiPolygon or
        geometryType == ogr.wkbMultiPolygon25D):
        if ogrgeometry.GetGeometryCount() > 1:
            geometry = Relation()
            for polygon in range(ogrgeometry.GetGeometryCount()):
                exterior = parseLineString(ogrgeometry.GetGeometryRef(polygon).GetGeometryRef(0))
                exterior.addparent(geometry)
                geometry.members.append((exterior, "outer"))
                for i in range(1, ogrgeometry.GetGeometryRef(polygon).GetGeometryCount()):
                    interior = parseLineString(ogrgeometry.GetGeometryRef(polygon).GetGeometryRef(i))
                    interior.addparent(geometry)
                    geometry.members.append((interior, "inner"))
            return [geometry]
        else:
           return [parsePolygon(ogrgeometry.GetGeometryRef(0))]
    elif (geometryType == ogr.wkbMultiLineString or
          geometryType == ogr.wkbMultiLineString25D):
        geometries = []
        for linestring in range(ogrgeometry.GetGeometryCount()):
            geometries.append(parseLineString(ogrgeometry.GetGeometryRef(linestring)))
        return geometries
    else:
        geometry = Relation()
        for i in range(ogrgeometry.GetGeometryCount()):
            member = parseGeometry(ogrgeometry.GetGeometryRef(i))
            member.addparent(geometry)
            geometry.members.append((member, "member"))
        return [geometry]


def mergeWayPoints():
    l.debug("Merging duplicate points in ways")
    ways = [geom for geom in Geometry.geometries if type(geom) == Way]

    # Remove duplicate points from ways,
    # a duplicate has the same id as its predecessor
    for way in ways:
        previous = OPTIONS.id
        merged_points = []

        for node in way.points:
            if previous == OPTIONS.id or previous != node.id:
                merged_points.append(node)
                previous = node.id

        if len(merged_points) > 0:
            way.points = merged_points


def splitLongWays(max_points_in_way, waysToCreateRelationFor):
    l.debug("Splitting long ways")
    ways = [geom for geom in Geometry.geometries if type(geom) == Way]

    featuresmap = {feature.geometry : feature for feature in Feature.features}


    for way in ways:
        is_way_in_relation = len([p for p in way.parents if type(p) == Relation]) > 0
        if len(way.points) > max_points_in_way:
            way_parts = splitWay(way, max_points_in_way, featuresmap, is_way_in_relation)
            if not is_way_in_relation:
                if way in waysToCreateRelationFor:
                    mergeIntoNewRelation(way_parts)
            else:
                for rel in way.parents:
                    splitWayInRelation(rel, way_parts)


def splitWay(way, max_points_in_way, features_map, is_way_in_relation):
    new_points = [way.points[i:i + max_points_in_way] for i in range(0, len(way.points), max_points_in_way - 1)]
    new_ways = [way, ] + [Way() for i in range(len(new_points) - 1)]

    if not is_way_in_relation:
        way_tags = features_map[way].tags

        for new_way in new_ways:
            if new_way != way:
                feat = Feature()
                feat.geometry = new_way
                feat.tags = way_tags

    for new_way, points in zip(new_ways, new_points):
        new_way.points = points
        if new_way.id != way.id:
            for point in points:
                point.removeparent(way, shoulddestroy=False)
                point.addparent(new_way)

    return new_ways


def mergeIntoNewRelation(way_parts):
    new_relation = Relation()
    feat = Feature()
    feat.geometry = new_relation
    new_relation.members = [(way, "outer") for way in way_parts]
    for way in way_parts:
        way.addparent(new_relation)


def splitWayInRelation(rel, way_parts):
    way_roles = [m[1] for m in rel.members if m[0] == way_parts[0]]
    way_role = "" if len(way_roles) == 0 else way_roles[0]
    for way in way_parts[1:]:
        rel.members.append((way, way_role))


def output():
    l.debug("Outputting XML")
    # First, set up a few data structures for optimization purposes
    nodes = [geom for geom in Geometry.geometries if type(geom) == Point]
    ways = [geom for geom in Geometry.geometries if type(geom) == Way]
    relations = [geom for geom in Geometry.geometries if type(geom) == Relation]
    featuresmap = {feature.geometry : feature for feature in Feature.features}

    # Open up the output file with the system default buffering
    with open(OPTIONS.outputFile, 'w', buffering=-1) as f:

        dec_string = '<?xml version="1.0"?>\n<osm version="0.6" generator="uvmogr2osm"'
        if OPTIONS.neverUpload:
            dec_string += ' upload="never"'
        elif not OPTIONS.noUploadFalse:
            dec_string += ' upload="false"'
        if OPTIONS.neverDownload:
            dec_string += ' download="never"'
        if OPTIONS.locked:
            dec_string += ' locked="true"'
        dec_string += '>\n'
        f.write(dec_string)

        # Build up a dict for optional settings
        attributes = {}
        if OPTIONS.addVersion:
            attributes.update({'version':'1'})

        if OPTIONS.addTimestamp:
            attributes.update({'timestamp':datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')})

        for node in nodes:
            xmlattrs = {'visible':'true','id':str(node.id), 'lat':str(node.y*10**-OPTIONS.significantDigits), 'lon':str(node.x*10**-OPTIONS.significantDigits)}
            xmlattrs.update(attributes)

            xmlobject = etree.Element('node', xmlattrs)

            if node in featuresmap:
                for (key, value) in featuresmap[node].tags.items():
                    tag = etree.Element('tag', {'k':key, 'v':value})
                    xmlobject.append(tag)
            if IS_PYTHON2:
                f.write(etree.tostring(xmlobject))
            else:
                f.write(etree.tostring(xmlobject, encoding='unicode'))
            f.write('\n')

        for way in ways:
            xmlattrs = {'visible':'true', 'id':str(way.id)}
            xmlattrs.update(attributes)

            xmlobject = etree.Element('way', xmlattrs)

            for node in way.points:
                nd = etree.Element('nd',{'ref':str(node.id)})
                xmlobject.append(nd)
            if way in featuresmap:
                for (key, value) in featuresmap[way].tags.items():
                    tag = etree.Element('tag', {'k':key, 'v':value})
                    xmlobject.append(tag)

            if IS_PYTHON2:
                f.write(etree.tostring(xmlobject))
            else:
                f.write(etree.tostring(xmlobject, encoding='unicode'))
            f.write('\n')

        for relation in relations:
            xmlattrs = {'visible':'true', 'id':str(relation.id)}
            xmlattrs.update(attributes)

            xmlobject = etree.Element('relation', xmlattrs)

            for (member, role) in relation.members:
                member = etree.Element('member', {'type':'way', 'ref':str(member.id), 'role':role})
                xmlobject.append(member)

            tag = etree.Element('tag', {'k':'type', 'v':'multipolygon'})
            xmlobject.append(tag)
            if relation in featuresmap:
                for (key, value) in featuresmap[relation].tags.items():
                    tag = etree.Element('tag', {'k':key, 'v':value})
                    xmlobject.append(tag)

            if IS_PYTHON2:
                f.write(etree.tostring(xmlobject))
            else:
                f.write(etree.tostring(xmlobject, encoding='unicode'))
            f.write('\n')

        f.write('</osm>')


def main():
    global TRANSLATIONS
    global OPTIONS
    global UNIQUE_NODE_INDEX
    global LONG_WAYS_FROM_POLYGONS

    # Setup program usage
    usage = """%prog SRCFILE

    SRCFILE can be a file path or a org PostgreSQL connection string such as:
    "PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes)"""
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-t", "--translation", dest="translationMethod",
                      metavar="TRANSLATION",
                      help="Select the attribute-tags translation method. See " +
                      "the translations/ directory for valid values.")
    parser.add_option("-o", "--output", dest="outputFile", metavar="OUTPUT",
                      help="Set destination .osm file name and location.")
    parser.add_option("-e", "--epsg", dest="sourceEPSG", metavar="EPSG_CODE",
                      help="EPSG code of source file. Do not include the " +
                           "'EPSG:' prefix. If specified, overrides projection " +
                           "from source metadata if it exists.")
    parser.add_option("-p", "--proj4", dest="sourcePROJ4", metavar="PROJ4_STRING",
                      help="PROJ.4 string. If specified, overrides projection " +
                           "from source metadata if it exists.")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_option("-d", "--debug-tags", dest="debugTags", action="store_true",
                      help="Output the tags for every feature parsed.")
    parser.add_option("-f", "--force", dest="forceOverwrite", action="store_true",
                      help="Force overwrite of output file.")

    parser.add_option("--encoding", dest="encoding",
                      help="Encoding of the source file. If specified, overrides " +
                      "the default of utf-8", default="utf-8")

    parser.add_option("--significant-digits",  dest="significantDigits", type=int,
                      help="Number of decimal places for coordinates", default=9)

    parser.add_option("--rounding-digits",  dest="roundingDigits", type=int,
                      help="Number of decimal places for rounding", default=7)

    parser.add_option("--no-memory-copy", dest="noMemoryCopy", action="store_true",
                        help="Do not make an in-memory working copy")

    parser.add_option("--no-upload-false", dest="noUploadFalse", action="store_true",
                        help="Omit upload=false from the completed file to surpress JOSM warnings when uploading.")

    parser.add_option("--never-download", dest="neverDownload", action="store_true",
                      help="Prevent JOSM from downloading more data to this file.")

    parser.add_option("--never-upload", dest="neverUpload", action="store_true",
                      help="Completely disables all upload commands for this file in JOSM, " +
                      "rather than merely showing a warning before uploading.")

    parser.add_option("--locked", dest="locked", action="store_true",
                      help="Prevent any changes to this file in JOSM, " +
                      "such as editing or downloading, and also prevents uploads. " +
                      "Implies upload=\"never\" and download=\"never\".")

    parser.add_option("--id", dest="id", type=int, default=0,
                        help="ID to start counting from for the output file. Defaults to 0.")

    parser.add_option("--idfile", dest="idfile", type=str, default=None,
                        help="Read ID to start counting from from a file.")

    parser.add_option("--split-ways", dest="maxNodesPerWay", type=int, default=1800,
                        help="Split ways with more than the specified number of nodes. Defaults to 1800. " +
                        "Any value below 2 - do not split.")

    parser.add_option("--saveid", dest="saveid", type=str, default=None,
                        help="Save last ID after execution to a file.")

    # Positive IDs can cause big problems if used inappropriately so hide the help for this
    parser.add_option("--positive-id", dest="positiveID", action="store_true",
                        help=optparse.SUPPRESS_HELP)

    # Add version attributes. Again, this can cause big problems so surpress the help
    parser.add_option("--add-version", dest="addVersion", action="store_true",
                        help=optparse.SUPPRESS_HELP)

    # Add timestamp attributes. Again, this can cause big problems so surpress the help
    parser.add_option("--add-timestamp", dest="addTimestamp", action="store_true",
                        help=optparse.SUPPRESS_HELP)

    parser.add_option("--sql", dest="sqlQuery", type=str, default=None,
                         help="SQL query to execute on a PostgreSQL source")

    parser.set_defaults(sourceEPSG=None, sourcePROJ4=None, verbose=False,
                        debugTags=False,
                        translationMethod=None, outputFile=None,
                        forceOverwrite=False, noUploadFalse=False,
                        neverDownload=False, neverUpload=False,
                        locked=False)

    # Parse and process arguments
    (OPTIONS, args) = parser.parse_args()

    try:
        if OPTIONS.sourceEPSG:
            OPTIONS.sourceEPSG = int(OPTIONS.sourceEPSG)
    except:
        parser.error("EPSG code must be numeric (e.g. '4326', not 'epsg:4326')")

    if len(args) < 1:
        parser.print_help()
        parser.error("you must specify a source filename")
    elif len(args) > 1:
        parser.error("you have specified too many arguments, " +
                     "only supply the source filename")

    if OPTIONS.addTimestamp:
        from datetime import datetime

    # Input and output file
    # if no output file given, use the basename of the source but with .osm
    source = args[0]
    sourceIsDatabase = bool(re.match('^PG:', source))

    if OPTIONS.outputFile is not None:
        OPTIONS.outputFile = os.path.realpath(OPTIONS.outputFile)
    elif sourceIsDatabase:
        parser.error("ERROR: An output file must be explicitly specified when using a database source")
    else:
        (base, ext) = os.path.splitext(os.path.basename(source))
        OPTIONS.outputFile = os.path.join(os.getcwd(), base + ".osm")

    if OPTIONS.sqlQuery and not sourceIsDatabase:
        parser.error("ERROR: You must use a database source when specifying a query with --sql")

    if not OPTIONS.forceOverwrite and os.path.exists(OPTIONS.outputFile):
        parser.error("ERROR: output file '%s' exists" % (OPTIONS.outputFile))
    l.info("Preparing to convert '%s' to '%s'." % (source, OPTIONS.outputFile))

    # Projection
    if not OPTIONS.sourcePROJ4 and not OPTIONS.sourceEPSG:
        l.info("Will try to detect projection from source metadata, or fall back to EPSG:4326")
    elif OPTIONS.sourcePROJ4:
        l.info("Will use the PROJ.4 string: " + OPTIONS.sourcePROJ4)
    elif OPTIONS.sourceEPSG:
        l.info("Will use EPSG:" + str(OPTIONS.sourceEPSG))

    # Stuff needed for locating translation methods
    if OPTIONS.translationMethod:
        # add dirs to path if necessary
        (root, ext) = os.path.splitext(OPTIONS.translationMethod)
        if os.path.exists(OPTIONS.translationMethod) and ext == '.py':
            # user supplied translation file directly
            sys.path.insert(0, os.path.dirname(root))
        else:
            # first check translations in the subdir translations of cwd
            sys.path.insert(0, os.path.join(os.getcwd(), "translations"))
            # then check subdir of script dir
            sys.path.insert(1, os.path.join(os.path.dirname(__file__), "translations"))
            # (the cwd will also be checked implicityly)

        # strip .py if present, as import wants just the module name
        if ext == '.py':
            OPTIONS.translationMethod = os.path.basename(root)

        try:
            TRANSLATIONS = __import__(OPTIONS.translationMethod, fromlist = [''])
        except ImportError as e:
            parser.error("Could not load translation method '%s'. Translation "
                   "script must be in your current directory, or in the "
                   "translations/ subdirectory of your current or ogr2osm.py "
                   "directory. The following directories have been considered: %s"
                   % (OPTIONS.translationMethod, str(sys.path)))
        except SyntaxError as e:
            parser.error("Syntax error in '%s'. Translation script is malformed:\n%s"
                   % (OPTIONS.translationMethod, e))

        l.info("Successfully loaded '%s' translation method ('%s')."
               % (OPTIONS.translationMethod, os.path.realpath(TRANSLATIONS.__file__)))
    else:
        import types
        TRANSLATIONS = types.ModuleType("translationmodule")
        l.info("Using default translations")

    default_translations = [
        ('filterLayer', lambda layer: layer),
        ('filterFeature', lambda feature, fieldNames, reproject: feature),
        ('filterTags', lambda tags: tags),
        ('filterFeaturePost', lambda feature, fieldNames, reproject: feature),
        ('preOutputTransform', lambda geometries, features: None),
        ]

    for (k, v) in default_translations:
        if hasattr(TRANSLATIONS, k) and getattr(TRANSLATIONS, k):
            l.debug("Using user " + k)
        else:
            l.debug("Using default " + k)
            setattr(TRANSLATIONS, k, v)

    Geometry.elementIdCounter = OPTIONS.id
    if OPTIONS.idfile:
        with open(OPTIONS.idfile, 'r') as ff:
            Geometry.elementIdCounter = int(ff.readline(20))
        l.info("Starting counter value '%d' read from file '%s'." \
            % (Geometry.elementIdCounter, OPTIONS.idfile))

    if OPTIONS.positiveID:
        Geometry.elementIdCounterIncr = 1 # default is -1

    # Main flow
    data = openData(source)
    LONG_WAYS_FROM_POLYGONS = set()
    parseData(data)
    mergeWayPoints()
    if OPTIONS.maxNodesPerWay >= 2:
        splitLongWays(OPTIONS.maxNodesPerWay, LONG_WAYS_FROM_POLYGONS)
    TRANSLATIONS.preOutputTransform(Geometry.geometries, Feature.features)
    output()
    if OPTIONS.saveid:
        with open(OPTIONS.saveid, 'w') as ff:
            ff.write(str(Geometry.elementIdCounter))
        l.info("Wrote elementIdCounter '%d' to file '%s'"
            % (Geometry.elementIdCounter, OPTIONS.saveid))


if __name__ == '__main__':
    main()

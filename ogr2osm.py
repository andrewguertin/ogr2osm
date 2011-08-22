#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" ogr2osm beta

 (c) Iván Sánchez Ortega, 2009
 <ivan@sanchezortega.es>


 This piece of crap^H^H^H^Hsoftware is supposed to take just about any vector
 file as an input thanks to the magic of the OGR libraries, and then output a
 pretty OSM XML file with that data.

 The cool part is that it will detect way segments shared between several ways,
 so it will build relations outof thin air. This simplifies the structure of
 boundaries, for example.

 It is also able to translate attributes to tags, though there is only one such
 translation scheme by now. In order to translate your own datasets, you should
 have some basic understanding of python programming. See the files in the
 translation/ directory.

 An outstanding issue is that elevation in 2.5D features (that can be generated
 by reprojecting) is ignored completely.

 Usage: specify a filename to be converted (its extension will be changed to
 .osm), and the the projection the source data is in. You can specify the
 source projection by using either an EPSG code or a Proj.4 string.

 If the projection is not specified, ogr2osm will try to fetch it from the
 source data. If there is no projection information in the source data, this
 will assume EPSG:4326 (WGS84 latitude-longitude).

 (-e and -p are mutually exclusive. If both are specified, only the last one
  will be taken into account)

 For example, if the shapefile foobar.shp has projection EPSG:23030, do:

 python ogr2osm.py foobar.shp -e 23030

 This will do an in-the-fly reprojection from EPSG:23030 to EPSG:4326, and
 write a file called "foobar.osm"


###############################################################################
#  "THE BEER-WARE LICENSE":                                                   #
#  <ivan@sanchezortega.es> wrote this file. As long as you retain this notice #
#  you can do whatever you want with this stuff. If we meet some day, and you #
#  think this stuff is worth it, you can buy me a beer in return.             #
###############################################################################
"""


import sys
import os
from optparse import OptionParser


try:
    from osgeo import ogr
except:
    import ogr

try:
    from osgeo import osr
except:
    import osr

# Some needed constants
from ogr import wkbPoint
from ogr import wkbLineString
from ogr import wkbPolygon
from ogr import wkbMultiPoint
from ogr import wkbMultiLineString
from ogr import wkbMultiPolygon
from ogr import wkbGeometryCollection

from ogr import wkbUnknown
from ogr import wkbNone

from ogr import wkbPoint25D
from ogr import wkbLineString25D
from ogr import wkbPolygon25D
from ogr import wkbMultiPoint25D
from ogr import wkbMultiLineString25D
from ogr import wkbMultiPolygon25D
from ogr import wkbGeometryCollection25D

from SimpleXMLWriter import XMLWriter

# Setup program usage
usage = "usage: %prog SRCFILE"
parser = OptionParser(usage=usage)
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
parser.add_option("-a", "--atribute-stats", dest="attributeStats",
                  action="store_true", help="Outputs a summary of the " +
                  "different tags / attributes encountered.")
parser.add_option("-f", "--force", dest="forceOverwrite", action="store_true",
                  help="Force overwrite of output file.")

parser.set_defaults(sourceEPSG=None, sourcePROJ4=None, verbose=False,
                    debugTags=False, attributeStats=False,
                    translationMethod=None, outputFile=None,
                    forceOverwrite=False)

# Parse and process arguments
(options, args) = parser.parse_args()

try:
    if options.sourceEPSG:
        options.sourceEPSG = int(options.sourceEPSG)
except:
    parser.error("EPSG code must be numeric (e.g. '4326', not 'epsg:4326')")

if len(args) < 1:
    parser.print_help()
    print "error: you must specify a source filename"
    sys.exit(1)
elif len(args) > 1:
    parser.error("you have specified too many arguments, " +
                 "only supply the source filename")


sourceFile = os.path.realpath(args[0])
if not os.path.isfile(sourceFile):
    parser.error("the file '%s' does not exist" % (sourceFile))

# if no output file given, use the basename of the source but with .osm
if options.outputFile is None:
    (base, ext) = os.path.splitext(os.path.basename(sourceFile))
    options.outputFile = os.path.join(os.getcwd(), base + ".osm")
options.outputFile = os.path.realpath(options.outputFile)

if not options.forceOverwrite and os.path.exists(options.outputFile):
    parser.error("ERROR: output file '%s' exists" % (options.outputFile))

dataSource = ogr.Open(sourceFile, 0)  # 0 means read-only
if dataSource is None:
    print ('ogr2osm.py: error: OGR failed to open ' + sourceFile +
           ', format may be unsuported')
    sys.exit(1)


print
print ("Preparing to convert file '%s' to '%s'."
       % (sourceFile, options.outputFile))

if not options.sourcePROJ4 and not options.sourceEPSG:
    print ("Will try to detect projection from source metadata, " +
           "or fall back to EPSG:4326")
elif options.sourcePROJ4:
    print "Will use the PROJ.4 string: " + options.sourcePROJ4
elif options.sourceEPSG:
    print "Will use EPSG:" + str(options.sourceEPSG)

showProgress = options.verbose
if showProgress:
    print "Verbose mode is on. Get ready to see lots of dots."

if options.debugTags:
    print "Tag debugging is on. Get ready to see lots of stuff."


# Some variables to hold stuff...
nodeIDsByXY = {}
nodeTags = {}
nodeCoords = {}
nodeRefs = {}
segmentNodes = {}
segmentIDByNodes = {}
segmentRefs = {}
areaRings = {}
areaTags = {}
lineSegments = {}
lineTags = {}

# nodeIDsByXY holds a node ID, given a set of coordinates (useful for
#   looking for duplicated nodes)
# nodeTags holds the tag pairs given a node ID
# nodeCoords holds the coordinates of a given node ID (redundant if
#   nodeIDsByXY is properly iterated through)
# nodeRefs holds up the IDs of any segment referencing (containing) a
#   given node ID, as a dictionary
# segmentNodes holds up the node IDs for a given segment ID
# segmentIDByNodes holds up segment IDs for a given pair of node IDs
#   (useful for looking for duplicated segments)
# segmentRefs holds up the IDs of any ways or areas referencing
#   (containing) a given segment ID, as a dictionary with segment IDs as
#   keys, and a boolean as value (the bool is a flag indicating whether
#   the segment is an existing segment, but reversed - will probably
#   screw things up with oneway=yes stuff)
# areaRings holds up the rings, as a list of segments, for a given area ID
# areaTags holds up the tags for a given area ID
# lineSegments and lineTags work pretty much as areaRings and areaTags
#   (only that lineSegments is a list, and areaRings is a list of lists)


# Stuff needed for locating translation methods
if options.translationMethod:
    # add dirs to path if necessary
    (root, ext) = os.path.splitext(options.translationMethod)
    if os.path.exists(options.translationMethod) and ext == '.py':
        # user supplied translation file directly
        sys.path.insert(0, os.path.dirname(root))
    else:
        # first check translations in the subdir translations of cwd
        sys.path.insert(0, os.path.join(os.getcwd(), "translations"))
        # then check subdir of script dir
        sys.path.insert(1, os.path.join(os.path.abspath(__file__),
                                        "translations"))
        # (the cwd will also be checked implicityly)

    # strip .py if present, as import wants just the module name
    if ext == '.py':
        options.translationMethod = os.path.basename(root)

    try:
        module = __import__(options.translationMethod)
        translateAttributes = module.translateAttributes
        translateAttributes([])
    except:
        print ("ERROR: Could not load translation method '%s'. Translation "
               "script must be in your current directory, or in the "
               "translations/ subdirectory of your current or ogr2osm.py "
               "directory.") % (options.translationMethod)
        sys.exit(-1)
    print ("Successfully loaded '%s' translation method ('%s')."
           % (options.translationMethod, os.path.realpath(module.__file__)))
else:
    # If no function has been defined, perform no translation:
    #   just copy everything.
    translateAttributes = lambda(attrs): attrs

elementIdCounter = -1
nodeCount = 0
segmentCount = 0
lineCount = 0
areaCount = 0
segmentJoinCount = 0


print
print "Parsing features"


# Some aux stuff for parsing the features into the data arrays

def addNode(x, y, tags={}):
    """
    Given x,y, returns the ID of an existing node there, or creates it
    and returns the new ID. Node will be updated with the optional tags.
    """
    global elementIdCounter, nodeCount, nodeCoords
    global nodeIDsByXY, nodeTags, nodeCoords

    if (x, y) in nodeIDsByXY:
        # Node already exists, merge tags
        #print
        #print "Warning, node already exists"
        nodeID = nodeIDsByXY[(x, y)]
        try:
            nodeTags[nodeID].update(tags)
        except:
            nodeTags[nodeID] = tags
        return nodeID
    else:
        # Allocate a new node
        nodeID = elementIdCounter
        elementIdCounter = elementIdCounter - 1

        nodeTags[nodeID] = tags
        nodeIDsByXY[(x, y)] = nodeID
        nodeCoords[nodeID] = (x, y)
        nodeCount = nodeCount + 1
        return nodeID


def lineStringToSegments(geometry, references):
    """
    Given a LineString geometry, will create the appropiate segments.
    It will add the optional tags and will not check for duplicate
    segments. Needs a line or area ID for updating the segment
    references. Returns a list of segment IDs.
    """
    global elementIdCounter, segmentCount, segmentNodes, segmentTags
    global showProgress, nodeRefs, segmentRefs, segmentIDByNodes

    result = []

    (lastx, lasty, z) = geometry.GetPoint(0)
    lastNodeID = addNode(lastx, lasty)

    for k in range(1, geometry.GetPointCount()):
        (newx, newy, z) = geometry.GetPoint(k)
        newNodeID = addNode(newx, newy)

        if (lastNodeID, newNodeID) in segmentIDByNodes:
            if showProgress:
                sys.stdout.write(u"-")
            segmentID = segmentIDByNodes[(lastNodeID, newNodeID)]
            reversed = False
            #print
            #print "Duplicated segment"
        elif (newNodeID, lastNodeID) in segmentIDByNodes:
            if showProgress:
                sys.stdout.write(u"_")
            segmentID = segmentIDByNodes[(newNodeID, lastNodeID)]
            reversed = True
            #print
            #print "Duplicated reverse segment"
        else:
            if showProgress:
                sys.stdout.write('.')
            segmentID = elementIdCounter

            elementIdCounter = elementIdCounter - 1
            segmentCount = segmentCount + 1
            segmentNodes[segmentID] = [lastNodeID, newNodeID]
            segmentIDByNodes[(lastNodeID, newNodeID)] = segmentID
            reversed = False

            try:
                nodeRefs[lastNodeID].update({segmentID: True})
            except:
                nodeRefs[lastNodeID] = {segmentID: True}
            try:
                nodeRefs[newNodeID].update({segmentID: True})
            except:
                nodeRefs[newNodeID] = {segmentID: True}

        try:
            segmentRefs[segmentID].update({references: reversed})
        except:
            segmentRefs[segmentID] = {references: reversed}

        result.append(segmentID)

        # FIXME
        segmentRefs

        lastNodeID = newNodeID
    return result


# Let's dive into the OGR data source and fetch the features

attributeStatsTable = {}
for i in range(dataSource.GetLayerCount()):
    layer = dataSource.GetLayer(i)
    layer.ResetReading()

    spatialRef = None
    if options.sourcePROJ4:
        spatialRef = osr.SpatialReference()
        spatialRef.ImportFromProj4(options.sourcePROJ4)
    elif options.sourceEPSG:
        spatialRef = osr.SpatialReference()
        spatialRef.ImportFromEPSG(options.sourceEPSG)
    else:
        spatialRef = layer.GetSpatialRef()
        if spatialRef != None:
            print "Detected projection metadata:"
            print spatialRef
        else:
            print "No projection metadata, falling back to EPSG:4326"

    if spatialRef == None:
        # No source proj specified yet? Then default to do no reprojection.
        # Some python magic: skip reprojection altogether by using a dummy
        # lamdba funcion. Otherwise, the lambda will be a call to the OGR
        # reprojection stuff.
        reproject = lambda(geometry): None
    else:
        destSpatialRef = osr.SpatialReference()
        # Destionation projection will *always* be EPSG:4326, WGS84 lat-lon
        destSpatialRef.ImportFromEPSG(4326)
        coordTrans = osr.CoordinateTransformation(spatialRef, destSpatialRef)
        reproject = lambda(geometry): geometry.Transform(coordTrans)

    featureDefinition = layer.GetLayerDefn()

    fieldNames = []
    fieldCount = featureDefinition.GetFieldCount()

    for j in range(fieldCount):
        #print featureDefinition.GetFieldDefn(j).GetNameRef()
        fieldNames.append(featureDefinition.GetFieldDefn(j).GetNameRef())
        if options.attributeStats:
            attributeStatsTable.update({
                featureDefinition.GetFieldDefn(j).GetNameRef(): {}})

    print
    print fieldNames
    print "Got layer field definitions"

    #print "Feature definition: " + str(featureDefinition);

    for j in range(layer.GetFeatureCount()):
        feature = layer.GetNextFeature()
        geometry = feature.GetGeometryRef()

        if geometry == None:
            continue

        fields = {}

        for k in range(fieldCount):
            #fields[ fieldNames[k] ] = feature.GetRawFieldRef(k)
            fields[fieldNames[k]] = feature.GetFieldAsString(k)
            if options.attributeStats:
                try:
                    attributeStatsTable[fieldNames[k]][feature.GetFieldAsString(k)] = \
                        attributeStatsTable[fieldNaddmes[k]][feature.GetFieldAsString(k)] + 1
                except:
                    attributeStatsTable[fieldNames[k]].update(
                        {feature.GetFieldAsString(k): 1})

        # Translate attributes into tags, as defined per the selected
        # translation method
        try:
            tags = translateAttributes(fields)
        except KeyError, err:
            print ("ERROR: Trying to access non-existent attribute key %s "
                   "in translation method."
                  % (err))
            sys.exit(-1)

        if options.debugTags:
            print
            print tags

        # Do the reprojection (or pass if no reprojection is neccesary,
        # see the lambda function definition)
        reproject(geometry)

        # Now we got the fields for this feature.
        # Now, let's convert the geometry.
        # Points will get converted into nodes.
        # LineStrings will get converted into a set of ways, each having
        #   only two nodes.
        # Polygons will be converted into relations.

        # Later, we'll fix the topology and simplify the ways. If a
        # relation can be simplified into a way (i.e. only has one member),
        # it will be. Adjacent segments will be merged if they share tags
        # and direction.

        # We'll split a geometry into subGeometries or "elementary"
        # geometries: points, linestrings, and polygons. This will take
        # care of OGRMultiLineStrings, OGRGeometryCollections and the like.

        geometryType = geometry.GetGeometryType()

        subGeometries = []

        if (geometryType == wkbPoint or
            geometryType == wkbLineString or
            geometryType == wkbPolygon):
            subGeometries = [geometry]
        elif (geometryType == wkbMultiPoint or
             geometryType == wkbMultiLineString or
             geometryType == wkbMultiPolygon or
             geometryType == wkbGeometryCollection):
            if showProgress:
                sys.stdout.write('M')
            for k in range(geometry.GetGeometryCount()):
                subGeometries.append(geometry.GetGeometryRef(k))

        elif (geometryType == wkbPoint25D or
              geometryType == wkbLineString25D or
              geometryType == wkbPolygon25D):
            if showProgress:
                sys.stdout.write('z')
            subGeometries = [geometry]
        elif (geometryType == wkbMultiPoint25D or
              geometryType == wkbMultiLineString25D or
              geometryType == wkbMultiPolygon25D or
              geometryType == wkbGeometryCollection25D):
            if showProgress:
                sys.stdout.write('Mz')
            for k in range(geometry.GetGeometryCount()):
                subGeometries.append(geometry.GetGeometryRef(k))

        elif geometryType == wkbUnknown:
            print "Geometry type is wkbUnknown, feature will be ignored\n"
        elif geometryType == wkbNone:
            print "Geometry type is wkbNone, feature will be ignored\n"
        else:
            print ("Unknown or unimplemented geometry type :" +
                   str(geometryType) + ", feature will be ignored\n")

        for geometry in subGeometries:
            if geometry.GetDimension() == 0:
                # 0-D = point
                if showProgress:
                    sys.stdout.write(',')
                x = geometry.GetX()
                y = geometry.GetY()

                nodeID = addNode(x, y, tags)
                # TODO: tags

            elif geometry.GetDimension() == 1:
                # 1-D = linestring
                if showProgress:
                    sys.stdout.write('|')

                lineID = elementIdCounter
                elementIdCounter = elementIdCounter - 1
                lineSegments[lineID] = lineStringToSegments(geometry, lineID)
                lineTags[lineID] = tags
                lineCount = lineCount + 1

            elif geometry.GetDimension() == 2:
                # FIXME
                # 2-D = area

                if showProgress:
                    sys.stdout.write('O')
                areaID = elementIdCounter
                elementIdCounter = elementIdCounter - 1
                rings = []

                for k in range(0, geometry.GetGeometryCount()):
                    if showProgress:
                        sys.stdout.write('r')
                    rings.append(lineStringToSegments(
                      geometry.GetGeometryRef(k), areaID))

                areaRings[areaID] = rings
                areaTags[areaID] = tags
                areaCount = areaCount + 1
                # TODO: tags
                # The ring 0 will be the outer hull, any other rings will be
                # inner hulls.

print
print "Nodes: " + str(nodeCount)
print "Way segments: " + str(segmentCount)
print "Lines: " + str(lineCount)
print "Areas: " + str(areaCount)

print
print "Joining segments"


# OK, all features should be parsed in the arrays by now
# Let's start to do some topological magic

# We'll iterate through all the lines and areas, then iterate through
# all the nodes contained there. We'll then fetch all segments
# referencing that node. If a pair of segments share the same references
# (i.e. they are part of the same line or area), they will be joined as
# one and de-referenced from that node. Joining segments mean than the
# concept of segment changes at this point, becoming linestrings or ways.
# There are some edge cases in which the algorithm may not prove optimal:
# if a line (or area ring) crosses itself, then the node will have more
# than two segments referenced to the line (or area), and does NOT
# check for the optimal one. As a result, lines that cross themselves
# may be (incorrectly) split into two and merged via a relation. In
# other words, the order of the points in a line (or ring) may not be
# kept if the line crosses itself.
# The algorithm will not check if the node has been de-referenced:
# instead, it will check for the first and last node of the segments
# involved - if the segments have already been joined, the check will fail.


def simplifyNode(nodeID):
    global nodeRefs, segmentNodes, segmentRefs, showProgress
    global lineSegments, areaRings, segmentJoinCount
    #for (nodeID, segments) in nodeRefs.items():
    segments = nodeRefs[nodeID]

    segmentsJoined = 0
    #print
    #print "Node ID: " + str(nodeID)
    #print "Node references to: " + str(segments)

    # We have to try all pairs of segments somehow
    for segmentID1 in segments.copy():
        # We'll be changing the references, so make sure we iterate through
        # the original list
        for segmentID2 in segments.copy():
            if segmentID1 != segmentID2:
                #print str(segmentID1) + " vs " + str(segmentID2)
                try:
                    if segmentNodes[segmentID1][-1] == segmentNodes[segmentID2][0] == nodeID and segmentRefs[segmentID1] == segmentRefs[segmentID2]:

                        #print "Segment " + str(segmentID1) + ": " + str(segmentNodes[segmentID1])
                        #print "Segment " + str(segmentID2) + ": " + str(segmentNodes[segmentID2])

                        #if showProgress: sys.stdout.write('=')
                        segmentNodes[segmentID1].extend(segmentNodes[segmentID2][1:])  # Voila! Joined!
                        for nodeShifted in segmentNodes[segmentID2][1:]:
                            # Replace node references
                            #print "deleting reference from node " + str(nodeShifted) + " to segment " + str(segmentID2) + "; updating to " + str(segmentID1)
                            del nodeRefs[nodeShifted][segmentID2]
                            nodeRefs[nodeShifted].update({segmentID1: True})

                        # TODO: Check for potential clashes between the
                        # references? As in "way X has these segments in the
                        # wrong direction". The trivial case for this looks
                        # like a topology error, anyway.
                        # Anyway, delete all references to the second segment
                        # - we're 100% sure that the line or area references
                        # the first one 'cause we've checked before joining the
                        # segments
                        for segmentRef in segmentRefs[segmentID2]:
                            try:
                                lineSegments[segmentRef].remove(segmentID2)
                            except:
                                for ring in areaRings[segmentRef]:
                                    try:
                                        ring.remove(segmentID2)
                                    except:
                                        pass

                        del segmentRefs[segmentID2]

                        del segmentNodes[segmentID2]
                        segmentJoinCount = segmentJoinCount + 1
                        segmentsJoined = segmentsJoined + 1
                except:
                    # This is due to the node no longer referencing to a
                    # segment because we just de-referenced it in a previous
                    # pass of the loop; this will be quite common
                    pass

    # FIXME: if segmentsJoined > 1, this should mark the node for further
    # testing - It's very likely to be a self-intersection.

    if showProgress:
        sys.stdout.write(str(segmentsJoined))

print
print "Simplifying line segments"
for line in lineSegments.values():
    #print line
    # No need to check the last segment, it could not be simplyfied
    for segmentID in line:
        #print segmentID
        #print segmentNodes[segmentID]
        for nodeID in segmentNodes[segmentID]:
            simplifyNode(nodeID)
            #simplifyNode(segmentNodes[segmentID][0])   # last node in segment

print
print "Simplifying area segments"
for area in areaRings.values():
    for ring in area:
        for segmentID in ring:
            for nodeID in segmentNodes[segmentID]:
                simplifyNode(nodeID)  # last node in segment


# That *should* do it... but a second pass through all the nodes will really
# fix things up. I wonder why some nodes are left out of the previous pass
print
print "Simplifying remaining nodes"
for node in nodeRefs.keys():
    simplifyNode(node)


print
print "Nodes: " + str(nodeCount)
print "Original way segments: " + str(segmentCount)
print "Segment join operations: " + str(segmentJoinCount)
print "Lines: " + str(lineCount)
print "Areas: " + str(areaCount)

#print nodeRefs
#print segmentNodes
#print lineSegments
#print areaRings
#print segmentRefs

print
print "Generating OSM XML..."
print "Generating nodes."

#w = XMLWriter(sys.stdout)
w = XMLWriter(open(options.outputFile, 'w'))

w.start("osm", version='0.6', generator='ogr2osm')

# First, the nodes
for (nodeID, (x, y)) in nodeCoords.items():
    w.start("node", visible="true", id=str(nodeID), lat=str(y), lon=str(x))
    for (tagKey, tagValue) in nodeTags[nodeID].items():
        if tagValue:
            w.element("tag", k=tagKey, v=tagValue)
    w.end("node")
    if showProgress:
        sys.stdout.write('.')


#print "Generated nodes. On to shared segments."

# Now, the segments used by more than one line/area, as untagged ways


#for (segmentID, segmentRef) in segmentRefs.items():
    #if len(segmentRef) > 1:
        #print "FIXME: output shared segment"
        #outputtedSegments[segmentID] = True


print
print "Generated nodes. On to lines."

# Next, the lines, either as ways or as relations

outputtedSegments = {}

for (lineID, lineSegment) in lineSegments.items():
    if showProgress:
        sys.stdout.write(str(len(lineSegment)) + " ")
    if len(lineSegment) == 1:   # The line will be a simple way
        w.start('way', id=str(lineID), action='modify', visible='true')

        for nodeID in segmentNodes[lineSegment[0]]:
            w.element('nd', ref=str(nodeID))

        for (tagKey, tagValue) in lineTags[lineID].items():
            if tagValue:
                w.element("tag", k=tagKey, v=tagValue)

        w.end('way')
        pass
    else:   # The line will be a relationship
        #print
        #print ("Line ID " + str(lineID) + " uses more than one segment: " +
        #       str(lineSegment))
        for segmentID in lineSegment:
            if segmentID not in outputtedSegments:
                w.start('way', id=str(segmentID), action='modify',
                        visible='true')
                for nodeID in segmentNodes[segmentID]:
                    w.element('nd', ref=str(nodeID))
                w.end('way')
        w.start('relation', id=str(lineID), action='modify', visible='true')
        for segmentID in lineSegment:
            w.element('member', type='way', ref=str(segmentID), role='')
        for (tagKey, tagValue) in lineTags[lineID].items():
            if tagValue:
                w.element("tag", k=tagKey, v=tagValue)
        w.end('relation')

print
print "Generated lines. On to areas."

# And last, the areas, either as ways or as relations

#print areaRings

for (areaID, areaRing) in areaRings.items():
    #sys.stdout.write(str(len(areaRings)))

    if len(areaRing) == 1 and len(areaRing[0]) == 1:
    # The area will be a simple way
        w.start('way', id=str(areaID), action='modify', visible='true')

        for nodeID in segmentNodes[areaRing[0][0]]:
            w.element('nd', ref=str(nodeID))

        for (tagKey, tagValue) in areaTags[areaID].items():
            if tagValue:
                w.element("tag", k=tagKey, v=tagValue)

        w.end('way')
        if showProgress:
            sys.stdout.write('0 ')
    else:
        segmentsUsed = 0
        segmentsUsedInRing = 0
        #print "FIXME"

        for ring in areaRing:
            for segmentID in ring:
                if segmentID not in outputtedSegments:
                    w.start('way', id=str(segmentID), action='modify',
                            visible='true')
                    for nodeID in segmentNodes[segmentID]:
                        w.element('nd', ref=str(nodeID))
                    w.end('way')

        w.start('relation', id=str(areaID), action='modify', visible='true')
        w.element("tag", k='type', v='multipolygon')

        role = 'outer'
        for ring in areaRing:
            for segmentID in ring:
                w.element('member', type='way', ref=str(segmentID), role=role)
                segmentsUsed = segmentsUsed + 1
                segmentsUsedInRing = segmentsUsedInRing + 1
            role = 'inner'
            #if showProgress: sys.stdout.write(str(segmentsUsedInRing)+'r')
            segmentsUsedInRing = 0

        for (tagKey, tagValue) in areaTags[areaID].items():
            if tagValue:
                w.element("tag", k=tagKey, v=tagValue)
        w.end('relation')
        if showProgress:
            sys.stdout.write(str(segmentsUsed) + " ")

if options.attributeStats:
    print
    for (attribute, stats) in attributeStatsTable.items():
        print "All values for attribute " + attribute + ":"
        print stats

print
print "All done. Enjoy your data!"

w.end("osm")

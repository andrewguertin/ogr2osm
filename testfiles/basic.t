  $ [ "$0" != "/bin/bash" ] || shopt -s expand_aliases
  $ [ -n "$PYTHON" ] || PYTHON="`which python`"
  $ alias ogr2osm="$PYTHON $TESTDIR/../ogr2osm.py"

usage:

  $ ogr2osm -h
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
  Options:
    -h, --help            show this help message and exit
    -t TRANSLATION, --translation=TRANSLATION
                          Select the attribute-tags translation method. See the
                          translations/ directory for valid values.
    -o OUTPUT, --output=OUTPUT
                          Set destination .osm file name and location.
    -e EPSG_CODE, --epsg=EPSG_CODE
                          EPSG code of source file. Do not include the 'EPSG:'
                          prefix. If specified, overrides projection from source
                          metadata if it exists.
    -p PROJ4_STRING, --proj4=PROJ4_STRING
                          PROJ.4 string. If specified, overrides projection from
                          source metadata if it exists.
    -v, --verbose         
    -d, --debug-tags      Output the tags for every feature parsed.
    -f, --force           Force overwrite of output file.
    --significant-digits=SIGNIFICANTDIGITS
                          Number of decimal places for coordinates
    --rounding-digits=ROUNDINGDIGITS
                          Number of decimal places for rounding
    --no-memory-copy      Do not make an in-memory working copy
    --no-upload-false     Omit upload=false from the completed file to surpress
                          JOSM warnings when uploading.
						  
test1:
  $ rm -f test1.osm
  $ ogr2osm $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_UTM_Zone_10N",
      GEOGCS["GCS_NAD83 [CSRS] 4.0.0.BC.1.GVRD_2005-04-05",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0]]
  Merging points
  Making list
  Checking list
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1.xml

duplicatefile:
  $ ogr2osm $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
  ogr2osm.py: error: ERROR: output file .*test1.osm' exists (re)
  [2]

force:
  $ ogr2osm -f $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_UTM_Zone_10N",
      GEOGCS["GCS_NAD83 [CSRS] 4.0.0.BC.1.GVRD_2005-04-05",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0]]
  Merging points
  Making list
  Checking list
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1.xml

nomemorycopy:
  $ ogr2osm -f --no-memory-copy $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_UTM_Zone_10N",
      GEOGCS["GCS_NAD83 [CSRS] 4.0.0.BC.1.GVRD_2005-04-05",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0]]
  Merging points
  Making list
  Checking list
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1.xml

positiveid:
  $ ogr2osm -f --positive-id $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_UTM_Zone_10N",
      GEOGCS["GCS_NAD83 [CSRS] 4.0.0.BC.1.GVRD_2005-04-05",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0]]
  Merging points
  Making list
  Checking list
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/positiveid.xml

version:
  $ ogr2osm -f --add-version $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_UTM_Zone_10N",
      GEOGCS["GCS_NAD83 [CSRS] 4.0.0.BC.1.GVRD_2005-04-05",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0]]
  Merging points
  Making list
  Checking list
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/version.xml

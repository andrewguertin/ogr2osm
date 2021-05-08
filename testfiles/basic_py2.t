  $ [ "$0" != "/bin/bash" ] || shopt -s expand_aliases
  $ [ -n "$PYTHON" ] || PYTHON="`which python`"
  $ alias ogr2osm="$PYTHON $TESTDIR/../ogr2osm.py"

usage:

  $ ogr2osm -h
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
      SRCFILE can be a file path or a org PostgreSQL connection string such as:
      "PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes)
  
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
    --encoding=ENCODING   Encoding of the source file. If specified, overrides
                          the default of utf-8
    --significant-digits=SIGNIFICANTDIGITS
                          Number of decimal places for coordinates
    --rounding-digits=ROUNDINGDIGITS
                          Number of decimal places for rounding
    --no-memory-copy      Do not make an in-memory working copy
    --no-upload-false     Omit upload=false from the completed file to surpress
                          JOSM warnings when uploading.
    --never-download      Prevent JOSM from downloading more data to this file.
    --never-upload        Completely disables all upload commands for this file
                          in JOSM, rather than merely showing a warning before
                          uploading.
    --locked              Prevent any changes to this file in JOSM, such as
                          editing or downloading, and also prevents uploads.
                          Implies upload="never" and download="never".
    --id=ID               ID to start counting from for the output file.
                          Defaults to 0.
    --idfile=IDFILE       Read ID to start counting from from a file.
    --split-ways=MAXNODESPERWAY
                          Split ways with more than the specified number of
                          nodes. Defaults to 1800. Any value below 2 - do not
                          split.
    --saveid=SAVEID       Save last ID after execution to a file.
    --sql=SQLQUERY        SQL query to execute on a PostgreSQL source
						  
test1:
  $ rm -f test1.osm
  $ ogr2osm $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1_py2.xml

duplicatefile:
  $ ogr2osm $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
      SRCFILE can be a file path or a org PostgreSQL connection string such as:
      "PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes)
  
  ogr2osm.py: error: ERROR: output file .*test1.osm' exists (re)
  [2]


force:
  $ ogr2osm -f $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1_py2.xml

nomemorycopy:
  $ ogr2osm -f --no-memory-copy $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/test1_py2.xml

positiveid:
  $ ogr2osm -f --positive-id $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/positiveid_py2.xml

version:
  $ ogr2osm -f --add-version $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format test1.osm | diff -uNr - $TESTDIR/version_py2.xml

timestamp:
  $ ogr2osm -f --add-timestamp $TESTDIR/shapefiles/test1.shp
  running with lxml.etree
  Preparing to convert .* (re)
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
          UNIT["Degree",0.017453292519943295],
          AUTHORITY["EPSG","4269"]],
      PROJECTION["Transverse_Mercator"],
      PARAMETER["False_Easting",500000.0],
      PARAMETER["False_Northing",0.0],
      PARAMETER["Central_Meridian",-123.0],
      PARAMETER["Scale_Factor",0.9996],
      PARAMETER["Latitude_Of_Origin",0.0],
      UNIT["Meter",1.0],
      AUTHORITY["EPSG","26910"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML

utf8:
  $ ogr2osm -f $TESTDIR/shapefiles/sp_usinas.shp
  running with lxml.etree
  Preparing to convert .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  Detected projection metadata:
  GEOGCS["GCS_South_American_1969",
      DATUM["South_American_Datum_1969",
          SPHEROID["GRS_1967_Modified",6378160.0,298.25]],
      PRIMEM["Greenwich",0.0],
      UNIT["Degree",0.0174532925199433]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format sp_usinas.osm | diff -uNr - $TESTDIR/utf8_py2.xml

japanese:
  $ ogr2osm --encoding shift_jis -f $TESTDIR/shapefiles/japanese.shp
  running with lxml.etree
  Preparing to convert .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  No projection metadata, falling back to EPSG:4326
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format japanese.osm | diff -uNr - $TESTDIR/japanese_py2.xml

duplicatewaynodes:
  $ ogr2osm -f $TESTDIR/shapefiles/duplicate-way-nodes.gml
  running with lxml.etree
  Preparing to convert .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Using default translations
  Using default filterLayer
  Using default filterFeature
  Using default filterTags
  Using default filterFeaturePost
  Using default preOutputTransform
  Parsing data
  No projection metadata, falling back to EPSG:4326
  Detected projection metadata:
  PROJCS["Amersfoort / RD New",
      GEOGCS["Amersfoort",
          DATUM["Amersfoort",
              SPHEROID["Bessel 1841",6377397.155,299.1528128,
                  AUTHORITY["EPSG","7004"]],
              TOWGS84[565.2369,50.0087,465.658,-0.406857,0.350733,-1.87035,4.0812],
              AUTHORITY["EPSG","6289"]],
          PRIMEM["Greenwich",0,
              AUTHORITY["EPSG","8901"]],
          UNIT["degree",0.0174532925199433,
              AUTHORITY["EPSG","9122"]],
          AXIS["Latitude",NORTH],
          AXIS["Longitude",EAST],
          AUTHORITY["EPSG","4289"]],
      PROJECTION["Oblique_Stereographic"],
      PARAMETER["latitude_of_origin",52.15616055555555],
      PARAMETER["central_meridian",5.38763888888889],
      PARAMETER["scale_factor",0.9999079],
      PARAMETER["false_easting",155000],
      PARAMETER["false_northing",463000],
      UNIT["metre",1,
          AUTHORITY["EPSG","9001"]],
      AXIS["X",EAST],
      AXIS["Y",NORTH],
      AUTHORITY["EPSG","28992"]]
  unhandled geometry, type: 10
  Detected projection metadata:
  PROJCS["Amersfoort / RD New",
      GEOGCS["Amersfoort",
          DATUM["Amersfoort",
              SPHEROID["Bessel 1841",6377397.155,299.1528128,
                  AUTHORITY["EPSG","7004"]],
              TOWGS84[565.2369,50.0087,465.658,-0.406857,0.350733,-1.87035,4.0812],
              AUTHORITY["EPSG","6289"]],
          PRIMEM["Greenwich",0,
              AUTHORITY["EPSG","8901"]],
          UNIT["degree",0.0174532925199433,
              AUTHORITY["EPSG","9122"]],
          AXIS["Latitude",NORTH],
          AXIS["Longitude",EAST],
          AUTHORITY["EPSG","4289"]],
      PROJECTION["Oblique_Stereographic"],
      PARAMETER["latitude_of_origin",52.15616055555555],
      PARAMETER["central_meridian",5.38763888888889],
      PARAMETER["scale_factor",0.9999079],
      PARAMETER["false_easting",155000],
      PARAMETER["false_northing",463000],
      UNIT["metre",1,
          AUTHORITY["EPSG","9001"]],
      AXIS["X",EAST],
      AXIS["Y",NORTH],
      AUTHORITY["EPSG","28992"]]
  Merging duplicate points in ways
  Splitting long ways
  Outputting XML
  $ xmllint --format duplicate-way-nodes.osm | diff -uNr - $TESTDIR/duplicate-way-nodes_py2.xml

require_output_file_when_using_db_source:

  $ ogr2osm "PG:dbname=test"
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
      SRCFILE can be a file path or a org PostgreSQL connection string such as:
      "PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes)
  
  ogr2osm.py: error: ERROR: An output file must be explicitly specified when using a database source
  [2]

require_db_source_for_sql_query:

  $ ogr2osm $TESTDIR/shapefiles/test1.shp --sql="SELECT * FROM wombats"
  running with lxml.etree
  Usage: ogr2osm.py SRCFILE
  
      SRCFILE can be a file path or a org PostgreSQL connection string such as:
      "PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes)
  
  ogr2osm.py: error: ERROR: You must use a database source when specifying a query with --sql
  [2]

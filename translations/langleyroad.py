'''
A translation function for Township of Langley Roads_shp.shp roads data. 

The shapefiles are availble under the PDDL as "Roads" from the Township of Langley 
at http://www.tol.ca/ServicesContact/OpenData/OpenDataCatalogue.aspx

The following fields are dropped from the source shapefile:

Field           Definition                  Reason
ALTROADNAM      Alternate name?             Always blank    
ALTSTNMID       Alternate name ID?          Always blank
FROMLEFTPR      From left property number   Belongs on different ways
FROMLEFTTH      From left theoretical       Not mappable
FROMRIGHTP      From right property number  Belongs on different ways
FROMRIGHTH      From right theoretical      Not mappable
OBJECTID        Internal feature number     Automatically generated
OWNER           Owner of road               Does not add to classification beyond ROADTYPE
PROJECTNUM      Project number              Always blank
ROADCLASS       Road class #                Text version of ROADTYPE
SHAPE_LEN       Length of feature           Automatically generated
STNAMEID        Unique ID for street name.  Not mappable
TOLEFTPROP      To left property number     Belongs on different ways
TOLEFTTHEO      To left theoretical         Not mappable
TORIGHTPRO      To left property number     Belongs on different ways
TORIGHTTHE      To left theoretical         Not mappable
YEARADDED       Year added to GIS database  Not mappable

The following fields are used:    

Field           Used for            Reason
ROADNAME        name=ROADNAME       Name of the road
ROADTYPE        highway=*           Type of the road
STREETID        tol:streetid    Unique ID for the road segment

Internal mappings:
OWNER=Provincial    <==> ROADTYPE=Highway Ramp|Ministry of Transportation
OWNER=Regional       ==> ROADTYPE=Major Road Network

OSM Mappings
Source value                            OSM value                           Shortcomings
ROADTYPE=Arterial                       highway=secondary           
ROADTYPE=Collector                      highway=tertiary            
ROADTYPE=Local                          highway=residential                 May need to be changed to highway=unclassified for some roads
ROADTYPE=Lane                           highway=service                     Source data does not indicate if service=alley
ROADTYPE=Gravel                         highway=residential surface=gravel
ROADTYPE=Ministry of Transportation     highway=primary|motorway            Huristics used to differentiate between highways. Double-check these
ROADTYPE=Major Road Network             highway=secondary                   Does not identify Highway 1A as primary
ROADTYPE=Highway Ramp                   highway=motorway_link
'''

def translateName(rawname):
    '''
    A general purpose name expander.
    '''
    suffixlookup = {
    'Ave':'Avenue',
    'Rd':'Road',
    'St':'Street',
    'Pl':'Place',
    'Cres':'Crescent',
    'Blvd':'Boulevard',
    'Dr':'Drive',
    'Lane':'Lane',
    'Crt':'Court',
    'Gr':'Grove',
    'Cl':'Close',
    'Rwy':'Railway',
    'Div':'Diversion',
    'Hwy':'Highway',
    'Hwy':'Highway',
    'Conn': 'Connector',
    'E':'East',
    'S':'South',
    'N':'North',
    'W':'West'}
	
    newName = ''
    for partName in rawname.split():
        newName = newName + ' ' + suffixlookup.get(partName,partName)

    return newName.strip()

    
def filterTags(attrs):
    if not attrs:
        return
    tags = {}
    
    if 'ROADNAME' in attrs:
        translated = translateName(attrs['ROADNAME'].title())
        if translated != '(Lane)' and translated != '(Ramp)':
            tags['name'] = translated
        
    if 'STREETID' in attrs:
        tags['tol:streetid'] = attrs['STREETID'].strip()
        
    if 'ROADTYPE' in attrs:
        if attrs['ROADTYPE'].strip() == 'Major Road Network':
            tags['highway'] = 'secondary'
        elif attrs['ROADTYPE'].strip() == 'Arterial':
            tags['highway'] = 'secondary'
        elif attrs['ROADTYPE'].strip() == 'Collector':
            tags['highway'] = 'tertiary'
        elif attrs['ROADTYPE'].strip() == 'Local':
            tags['highway'] = 'residential'
        elif attrs['ROADTYPE'].strip() == 'Lane':
            tags['highway'] = 'service'
        elif attrs['ROADTYPE'].strip() == 'Gravel':
            tags['highway'] = 'residential'
            tags['surface'] = 'gravel'
        elif attrs['ROADTYPE'].strip() == 'Ministry of Transportation':
            if translated and (translated == '#1 Highway' or translated == 'Golden Ears Bridge'):
                tags['highway'] = 'motorway'
            else:
                tags['highway'] = 'primary'
        elif attrs['ROADTYPE'].strip() == 'Highway Ramp':
            tags['highway'] = 'motorway_link'
        else:
            tags['highway'] = 'road'
            tags['tol:roadtype'] = attrs['ROADTYPE'].strip()
            
        tags['source'] = 'Township of Langley GIS Data'

    return tags
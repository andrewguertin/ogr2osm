from osgeo import ogr
import re
import urllib
import json

uvmfeatures = []

def filterLayer(layer):
    if layer is None:
        return None
    print layer.GetName()
    return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        return
    layer = ogrfeature.GetFieldAsString("Layer")
    if (layer == "VA-BLDG-UVM" or
        layer == "VA-BLDG-NON UVM"):
        return ogrfeature
    elif (layer == "VA-BLDG-ATTRIBUTES" and len(ogrfeature.GetFieldAsString("Text")) == 4):
        # Ignore CFC Soccer Stands - has no building outline
        if ogrfeature.GetFieldAsString("Text") == "0979":
            return
        return ogrfeature
    else:
        return

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None and ogrfeature is None and ogrgeometry is None:
        return
    global uvmfeatures
    uvmfeatures.append((feature, ogrfeature, ogrgeometry))

def filterTags(tags):
    if tags is None:
        return
    newtags = {}
    for (key, value) in tags.items():
        if (key == "Layer" or 
            (key == "Text" and value != "")):
            newtags[key] = value
        if (key == "Layer" and value != "VA-UVM-BLDG-CODE"):
            newtags["building"] = "yes"
    return newtags
        

def preOutputTransform(geometries, features):
    if geometries is None and features is None:
        return
    global uvmfeatures
    buildingcodes = [(feature, ogrfeature, ogrgeometry) for (feature, ogrfeature, ogrgeometry) in uvmfeatures if ogrfeature.GetFieldAsString("Layer") == "VA-BLDG-ATTRIBUTES"]
    buildings = [x for x in uvmfeatures if x not in buildingcodes]
    # Match each code to the closest building, setting the building's feature's
    # name
    for (codef, codeogrf, codeogrg) in buildingcodes:
        dist = float("inf")
        chosenfeature = (None, None, None)
        for (bldgf, bldgogrf, bldgogrg) in buildings:
            newdist = codeogrg.Distance(bldgogrg)
            if newdist < dist:
                dist = newdist
                chosenfeature = (bldgf, bldgogrf, bldgogrg)
        (bldgf, bldgogrf, bldgogrg) = chosenfeature
        buildingid = codeogrf.GetFieldAsString("Text")
        if bldgf.tags.has_key("uvm:buildingid") and bldgf.tags["uvm:buildingid"] != buildingid:
            print "WARNING: buildingid overlap detected! " + bldgf.tags["uvm:buildingid"] + " " + buildingid
        bldgf.tags["uvm:buildingid"] = buildingid
        page = urllib.urlopen("http://www-dev.uvm.edu/~aguertin/webteam/map/famis/getbldgname.php?BLDG="+buildingid)
        name = page.read()
        page.close
        bldgf.tags["name"] = name

    # Remove the building code nodes
    for feature in [f for f in features if f.tags["Layer"] == "VA-BLDG-ATTRIBUTES"]:
        print "Removing a text node: " + feature.tags["Text"]
        features.remove(feature)
        feature.geometry.removeparent(feature)
    
    # Remove buildings that were not given a buildingid
    for feature in [f for f in features if "uvm:buildingid" not in f.tags]:
        features.remove(feature)
        try:
            geometries.remove(feature.geometry)
            try:
                for point in set(feature.geometry.points):
                    try:
                        point.removeparent(feature.geometry)
                    except:
                        print "What went wrong here???"
            except:
                print "Failed -- geometry.points does not exist -- not a way"
        except:
            print "Failed -- two building features with same geometry??"

    uvmjson(geometries, features)

def uvmjson(geometries, features):
    print "IN UVMJSON"
    buildings = [building for building in features if "uvm:buildingid" in building.tags]
    outbuildings = []
    for building in buildings:
        outbuilding = {}
        outbuilding["id"] = building.tags["uvm:buildingid"]
        outbuilding["geometry"] = []
        if str(type(building.geometry)) != "<class '__main__.Way'>":
            print "WARNING: building not way, being ignored!"
            print str(type(building.geometry))
        else:
            for point in building.geometry.points:
                outbuilding["geometry"].append({"x": point.x, "y": point.y})
        outbuildings.append(outbuilding)
    f = open('/tmp/uvmbuildings.json', 'w')
    f.write(json.dumps(outbuildings, indent=4))
    f.close()

from osgeo import ogr
import re

def filterLayer(layer):
    if layer is None:
    	return None
    print layer.GetName()
    return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        return
    tags = {}
    for i in range(len(fieldNames)):
        tags[fieldNames[i]] = ogrfeature.GetFieldAsString(i)
    if (tags["Layer"] != "VA-BLDG-MAJR" and
        tags["Layer"] != "VA-BLDG-MINR" and
        tags["Layer"] != "VA-BLDG-OTHR" and
       	tags["Layer"] != "VA-UVM-BLDG-CODE"):
        return
    else:
        return ogrfeature

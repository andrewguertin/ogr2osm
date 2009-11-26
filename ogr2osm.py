#!/usr/local/bin/python
# -*- coding: utf-8 -*-


#
# ogr2osm alpha
# 
# (c) Iván Sánchez Ortega, 2009 
# <ivan@sanchezortega.es>
#
#
# This piece of crap^H^H^H^Hsoftware is supposed to take just about any vector file 
# as an input thanks to the magic of the OGR libraries, and then output a pretty OSM XML
# file with that data.
#
# The cool part is that it will detect way segments shared between several ways, so
# it will build relations outof thin air. This simplifies the structure of boundaries, for
# example.
#
# This is in a alpha state, meaning "it works if you tweak it right". In order for this to work,
# you have to manually edit the input and output filenames, and check that the right OGR data
# driver is selected.
#
# Another gotcha is that there is no tag conversion, yet. The original attributes of the vector
# data will be used as tags.
#
#
##################################################################################
#   "THE BEER-WARE LICENSE":
#   <ivan@sanchezortega.es> wrote this file. As long as you retain this notice you
#   can do whatever you want with this stuff. If we meet some day, and you think
#   this stuff is worth it, you can buy me a beer in return.
##################################################################################
#
#
#




import sys
from SimpleXMLWriter import XMLWriter

try:
	from osgeo import ogr
except:
	import ogr

# Some needed constants
from ogr import wkbPoint 
from ogr import wkbLineString  
from ogr import wkbPolygon  
from ogr import wkbMultiPoint   
from ogr import wkbMultiLineString  
from ogr import wkbMultiPolygon   
from ogr import wkbGeometryCollection   



file = 'BCN200/Soriatt01_4326.dgn';
driver = ogr.GetDriverByName('DGN');

outputFile = 'Soriatt01.osm'

# 0 means read-only
dataSource = driver.Open(file,0); 

if dataSource is None:
	print 'Could not open ' + file
	sys.exit(1)



# Some variables to hold stuff...
nodeIDsByXY  = {}
nodeTags     = {}
nodeCoords   = {}
nodeRefs     = {}
segmentNodes = {}
segmentIDByNodes = {}
segmentRefs  = {}
areaRings    = {}
areaTags     = {}
lineSegments = {}
lineTags     = {}

# nodeIDsByXY holds a node ID, given a set of coordinates (useful for looking for duplicated nodes)
# nodeTags holds the tag pairs given a node ID
# nodeCoords holds the coordinates of a given node ID (redundant if nodeIDsByXY is properly iterated through)
# nodeRefs holds up the IDs of any segment referencing (containing) a given node ID, as a dictionary
# segmentNodes holds up the node IDs for a given segment ID
# segmentIDByNodes holds up segment IDs for a given pair of node IDs (useful for looking for duplicated segments)
# segmentRefs holds up the IDs of any ways or areas referencing (containing) a given segment ID, as a dictionary with segment IDs as keys, and a boolean as value (the bool is a flag indicating whether the segment is an existing segment, but reversed - will probably screw things up with oneway=yes stuff)
# areaRings holds up the rings, as a list of segments, for a given area ID
# areaTags holds up the tags for a given area ID
# lineSegments and lineTags work pretty much as areaRings and areaTags (only that lineSegments is a list, and areaRings is a list of lists)


elementIdCounter = -1
nodeCount = 0
segmentCount = 0
lineCount = 0
areaCount = 0
segmentJoinCount = 0

showProgress = True


print
print "Parsing features"


# Some aux stuff for parsing the features into the data arrays

def addNode(x,y,tags = {}):
	"Given x,y, returns the ID of an existing node there, or creates it and returns the new ID. Node will be updated with the optional tags."
	global elementIdCounter, nodeCount, nodeCoords, nodeIDsByXT, nodeTags, nodeCoords
	
	if (x,y) in nodeIDsByXY:
		# Node already exists, merge tags
		#print
		#print "Warning, node already exists"
		nodeID = nodeIDsByXY[(x,y)]
		try:
			nodeTags[nodeID].update(tags)
		except:
			nodeTags[nodeID]=tags
		return nodeID
	else:
		# Allocate a new node
		nodeID = elementIdCounter
		elementIdCounter = elementIdCounter - 1
		
		nodeTags[nodeID]=tags
		nodeIDsByXY[(x,y)] = nodeID
		nodeCoords[nodeID] = (x,y)
		nodeCount = nodeCount +1	
		return nodeID
	
	
def lineStringToSegments(geometry,references):
	"Given a LineString geometry, will create the appropiate segments. It will add the optional tags and will not check for duplicate segments. Needs a line or area ID for updating the segment references. Returns a list of segment IDs."
	global elementIdCounter, segmentCount, segmentNodes, segmentTags, showProgress, nodeRefs, segmentRefs, segmentIDByNodes
	
	result = []
	
	(lastx,lasty,z) = geometry.GetPoint(0)
	lastNodeID = addNode(lastx,lasty)
	
	for k in range(1,geometry.GetPointCount()):
		
		(newx,newy,z) = geometry.GetPoint(k)
		newNodeID = addNode(newx,newy)
		
		if (lastNodeID, newNodeID) in segmentIDByNodes:
			if showProgress: sys.stdout.write(u"-")
			segmentID = segmentIDByNodes[(lastNodeID, newNodeID)]
			reversed = False
			#print
			#print "Duplicated segment"
		elif (newNodeID, lastNodeID) in segmentIDByNodes:
			if showProgress: sys.stdout.write(u"_")
			segmentID = segmentIDByNodes[(newNodeID, lastNodeID)]
			reversed = True
			#print
			#print "Duplicated reverse segment"
		else:
			if showProgress: sys.stdout.write('.')
			segmentID = elementIdCounter
			
			elementIdCounter = elementIdCounter - 1
			segmentCount = segmentCount +1
			segmentNodes[segmentID] = [ lastNodeID, newNodeID ]
			segmentIDByNodes[(lastNodeID, newNodeID)] = segmentID
			reversed = False
			
			try:
				nodeRefs[lastNodeID].update({segmentID:True})
			except:
				nodeRefs[lastNodeID]={segmentID:True}
			try:
				nodeRefs[newNodeID].update({segmentID:True})
			except:
				nodeRefs[newNodeID]={segmentID:True}
		
		
		try:
			segmentRefs[segmentID].update({references:reversed})
		except:
			segmentRefs[segmentID]={references:reversed}

		result.append(segmentID)
		
		# FIXME
		segmentRefs
		
		lastNodeID = newNodeID
	return result







# Let's dive into the OGR data source and fetch the features

for i in range(dataSource.GetLayerCount()):
	layer = dataSource.GetLayer(i)
	layer.ResetReading()
	featureDefinition = layer.GetLayerDefn()
	
	fieldNames = []
	fieldCount = featureDefinition.GetFieldCount();
	
	for j in range(fieldCount):
		#print featureDefinition.GetFieldDefn(j).GetNameRef()
		fieldNames.append (featureDefinition.GetFieldDefn(j).GetNameRef())
	
	print
	print fieldNames
	print "Got layer field definitions"
	
	#print "Feature definition: " + str(featureDefinition);
	
	for j in range(layer.GetFeatureCount()):
		feature = layer.GetNextFeature()
		geometry = feature.GetGeometryRef()
		
		fields = {}
		
		for k in range(fieldCount-1):
			#fields[ fieldNames[k] ] = feature.GetRawFieldRef(k)
			fields[ fieldNames[k] ] = feature.GetFieldAsString(k)
		
		
		
		#print fields
		
		# TODO: Now it should be a good time to apply attributes->tags conversion rules!!
		
		tags = fields
		
		# Now we got the fields for this feature. Now, let's convert the geometry.
		# Points will get converted into nodes.
		# LineStrings will get converted into a set of ways, each having only two nodes
		# Polygons will be converted into relations
		# Later, we'll fix the topology and simplify the ways. If a relation can be simplified into a way (i.e. only has one member), it will be. Adjacent segments will be merged if they share tags and direction.
		
		# We'll split a geometry into subGeometries or "elementary" geometries: points, linestrings, and polygons. This will take care of OGRMultiLineStrings, OGRGeometryCollections and the like
		
		#try:
		geometryType = geometry.GetGeometryType()
		#except:
			#print geometry
			#print type(geometry)
			#print dir(geometry)
			#print geometry.GetGeometryType()
		
		subGeometries = []
		
		if geometryType == wkbPoint or geometryType == wkbLineString or geometryType == wkbPolygon:
			subGeometries = [geometry]
		elif geometryType == wkbMultiPoint or geometryType == wkbMultiLineString or geometryType == wkbMultiPolygon or geometryType == OGRGeometryCollection:
			sys.stdout.write('M')
			for k in range(geometry.GetGeometryCount()):
				subGeometries.append(geometry.GetGeometryRef(k))
		else:
			print "Unknown geometry type (or unimplemented 2.5D geometry type), feature will be ignored\n"
		
		
		for geometry in subGeometries:
			if geometry.GetDimension() == 0:
				# 0-D = point
				if showProgress: sys.stdout.write(',')
				x = geometry.GetX()
				y = geometry.GetY()
				
				nodeID = addNode(x,y,tags)
				# TODO: tags
				
			elif geometry.GetDimension() == 1:
				# 1-D = linestring
				if showProgress: sys.stdout.write('|')
				
				lineID = elementIdCounter
				elementIdCounter = elementIdCounter - 1
				lineSegments[lineID] = lineStringToSegments(geometry,lineID)
				lineTags[lineID] = tags
				lineCount = lineCount + 1
				
			elif geometry.GetDimension() == 2:
				# FIXME
				# 2-D = area
				
				if showProgress: sys.stdout.write('O')
				areaID = elementIdCounter
				elementIdCounter = elementIdCounter - 1
				rings = []
				
				for k in range(0,geometry.GetGeometryCount()):
					if showProgress: sys.stdout.write('r')
					rings.append(lineStringToSegments(geometry.GetGeometryRef(k), areaID))
				
				areaRings[areaID] = rings
				areaTags[areaID]  = tags
				areaCount = areaCount + 1
				# TODO: tags
				# The ring 0 will be the outer hull, any other rings will be inner hulls.
	
	
	
print
print "Nodes: " + str(nodeCount)
print "Way segments: " + str(segmentCount)
print "Lines: " + str(lineCount)
print "Areas: " + str(areaCount)
	
print
print "Joining segments"

	
# OK, all features should be parsed in the arrays by now
# Let's start to do some topological magic

# We'll iterate through all the nodes, and fetch all segments referencing that node. If a pair of segments share the same references (i.e. they are part of the same line or area), they will be joined as one and de-referenced from that node. Joining segments mean than the concept of segment changes at this point, becoming linestrings or ways.
# There are some edge cases in which the algorithm may not prove optimal: if a line (or area ring) crosses itself, then the node will have more than two segments referenced to the line (or area), and does NOT check for the optimal one. As a result, lines that cross themselves may be (incorrectly) split into two and merged via a relation. In other words, the order of the points in a line (or ring) may not be kept if the line crosses itself.
# The algorithm will not check if the node has been de-referenced: instead, it will check for the first and last node of the segments involved - if the segments have already been joined, the check will fail.


#print nodeRefs
#print nodeRefs.iteritems()
#print dir(nodeRefs)

for (nodeID, segments) in nodeRefs.items():
	#print
	#print "Node ID: " + str(nodeID)
	#print "Node references to: " + str(segments)
	
	# We have to try all pairs of segments somehow
	for segmentID1 in segments.copy():
		for segmentID2 in segments.copy():	# We'll be changing the references, so make sure we iterate through the original list
			if segmentID1 != segmentID2:
				#print str(segmentID1) + " vs " + str(segmentID2)
				try:
					if segmentNodes[segmentID1][-1] == segmentNodes[segmentID2][0] == nodeID and segmentRefs[segmentID1] == segmentRefs[segmentID2] :
						
						#print "Segment " + str(segmentID1) + ": " + str(segmentNodes[segmentID1])
						#print "Segment " + str(segmentID2) + ": " + str(segmentNodes[segmentID2])
						
						if showProgress: sys.stdout.write('=')
						segmentNodes[segmentID1].extend( segmentNodes[segmentID2][1:] )	# Voila! Joined!
						for nodeShifted in segmentNodes[segmentID2][1:]:	# Replace node references
							#print "deleting reference from node " + str(nodeShifted) + " to segment " + str(segmentID2) + "; updating to " + str(segmentID1)
							del nodeRefs[nodeShifted][segmentID2]
							nodeRefs[nodeShifted].update({segmentID1:True})
						
						# TODO: Check for potential clashes between the references? As in "way X has these segments in the wrong direction". The trivial case for this looks like a topology error, anyway.
						# Anyway, delete all references to the second segment - we're 100% sure that the line or area references the first one 'cause we've checked before joining the segments
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
						segmentJoinCount = segmentJoinCount +1
				except:
					pass	# This is due to the node no longer referencing to a segment because we just de-referenced it in a previous pass of the loop; this will be quite common
	


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
w = XMLWriter(open(outputFile,'w'))

w.start("osm", version='0.6', generator='ogr2osm')

# First, the nodes
for (nodeID,(x,y)) in nodeCoords.items():
	w.start("node", visible="true", id=str(nodeID), lat=str(y), lon=str(x))
	for (tagKey,tagValue) in nodeTags[nodeID].items():
		if tagValue:
			w.element("tag", k=tagKey, v=tagValue)
	w.end("node")
	if showProgress: sys.stdout.write('.')


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
	if showProgress: sys.stdout.write(str(len(lineSegment)) + " ")
	if len(lineSegment) == 1:	# The line will be a simple way
		w.start('way', id=str(lineID), action='modify', visible='true')
		
		for nodeID in segmentNodes[ lineSegment[0] ]:
			w.element('nd',ref=str(nodeID))
		
		for (tagKey,tagValue) in lineTags[lineID].items():
			if tagValue:
				w.element("tag", k=tagKey, v=tagValue)
		
		w.end('way')
		pass
	else:	# The line will be a relationship
		#print
		#print "Line ID " + str(lineID) + " uses more than one segment: " + str(lineSegment)
		for segmentID in lineSegment:
			if segmentID not in outputtedSegments:
				w.start('way', id=str(segmentID), action='modify', visible='true')
				for nodeID in segmentNodes[ segmentID ]:
					w.element('nd',ref=str(nodeID))
				w.end('way')
		w.start('relation', id=str(lineID), action='modify', visible='true')
		for segmentID in lineSegment:
			w.element('member', type='way', ref=str(segmentID), role='')
		for (tagKey,tagValue) in lineTags[lineID].items():
			if tagValue:
				w.element("tag", k=tagKey, v=tagValue)
		w.end('relation')

print
print "Generated lines. On to areas."

# And last, the areas, either as ways or as relations

#print areaRings

for (areaID, areaRing) in areaRings.items():
	#sys.stdout.write(str(len(areaRings)))
	
	if len(areaRings) == 1 and len(areaRings.values()[0][0]) == 1: # The area will be a simple way
		w.start('way', id=str(areaID), action='modify', visible='true')
		
		for nodeID in segmentNodes[ areaRings.values()[0][0][0] ]:  # Geez. [0][0][0]
			w.element('nd',ref=str(nodeID))
		
		for (tagKey,tagValue) in areaTags[areaID].items():
			if tagValue:
				w.element("tag", k=tagKey, v=tagValue)
		
		w.end('way')		
		if showProgress: sys.stdout.write('0 ')
	else:
		segmentsUsed = 0
		#print "FIXME"
		
		for ring in areaRing:
			for segmentID in ring:
				if segmentID not in outputtedSegments:
					w.start('way', id=str(segmentID), action='modify', visible='true')
					for nodeID in segmentNodes[ segmentID ]:
						w.element('nd',ref=str(nodeID))
					w.end('way')
				
		
		w.start('relation', id=str(areaID), action='modify', visible='true')
		w.element("tag", k='type', v='multipolygon')
		
		role = 'outer'
		for ring in areaRing:
			for segmentID in ring:
				w.element('member', type='way', ref=str(segmentID), role=role)
				segmentsUsed = segmentsUsed + 1
			role = 'inner'
	
		for (tagKey,tagValue) in areaTags[areaID].items():
			if tagValue:
				w.element("tag", k=tagKey, v=tagValue)
		w.end('relation')
		if showProgress: sys.stdout.write(str(segmentsUsed) + " ")


print
print "All done. Enjoy your data!"


w.end("osm")








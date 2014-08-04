#!/usr/bin/env python

# Author: Jesus Galaz, 02/Feb/2013, last update 24/July/2014
# Copyright (c) 2011 Baylor College of Medicine
#
# This software is issued under a joint BSD/GNU license. You may use the
# source code in this file under either license. However, note that the
# complete EMAN2 and SPARX software packages have some GPL dependencies,
# so you are responsible for compliance with the licenses of these packages
# if you opt to use BSD licensing. The warranty disclaimer below holds
# in either instance.
#
# This complete copyright notice must be included in any revised version of the
# source code. Additional authorship citations may be added, but existing
# author citations must be preserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  2111-1307 USA


import os
from EMAN2 import *
import sys
import time
import numpy
import pylab
#from operator import itemgetter
from matplotlib.ticker import MaxNLocator
from pylab import figure, show	
import matplotlib.pyplot as plt
import math


def main():
	progname = os.path.basename(sys.argv[0])
	usage = """UNDER DEVELOPOMENT. Extracts particles from each image in an aligned tilt series based on their position in the reconstructed tomogram."""

	parser = EMArgumentParser(usage=usage,version=EMANVERSION)
	
	'''
	Parameters for adding ctf and noise
	'''
	parser.add_argument('--tiltseries',type=str,default='',help="""File in .ali, .mrc or .hdf 
		format of the aligned tiltseries.""")
		
	parser.add_argument('--tiltangles',type=str,default='',help="""File in .tlt or .txt format 
		containing the tilt angle of each tilt image in the tiltseries.""")
		
	parser.add_argument('--coords',type=str,default='',help="""File in .txt format containing 
		the coordinates of particles determined from the reconstructed tomogram of the 
		supplied tiltseries.""")
	
	parser.add_argument('--path',type=str,default='spt_subtilt',help="""Directory to save 
		the results.""")
	
	parser.add_argument('--boxsize',type=int,default=128,help="""Size of the 2D "tiles" or 
		images for each particle from each image in the tiltseries.""")
	
	parser.add_argument("--ppid", type=int, help="""Set the PID of the parent process, 
		used for cross platform PPID""",default=-1)
	
	parser.add_argument("--verbose", "-v", dest="verbose", action="store", metavar="n",type=int, default=0, help="verbose level [0-9], higner number means higher level of verboseness")
	
	parser.add_argument('--subset', type=int, default=0, help='''Specify how many sub-tiltseries 
		(or particles) from the coordinates file you want to extract; e.g, if you specify 10, 
		the first 10 particles will be boxed.\n0 means "box them all" because it makes no 
		sense to box none''')
	
	#parser.add_argument('--tomogramthickness',type=int,default=None,help='Z dimension of the reconstructed tomogram.')
	
	parser.add_argument('--tomosides',type=str,default='',help="""Comma separated values 
		for the tomogram dimensions. Alternatively, provide the path to the tomogram itself 
		through --tomogram.""")
	
	parser.add_argument('--tomogram',type=str,default='',help='Path to the tomogram.')
	
	parser.add_argument("--shrink", type=int,default=1,help="""Optionally shrink the coordinates 
		by a factor of --shrink=N to speed up the process. Might compromise accuracy if two 
		points in the coordinates file are very close to eachother.""")
	
	parser.add_argument('--cshrink', type=int, default=1, help='''Specifies the factor by 
		which to multiply the coordinates in the coordinates file, so that they can be at 
		the same scale as the tomogram. For example, provide 2 if the coordinates are on a 
		2K x 2K scale, but you want to extract the sub-volumes from the UN-shrunk 4K x 4K
		tomogram.''')
	
	parser.add_argument("--everyother", type=int, help="""Pick every other tilt. For example, 
		--tilt=3 would pick every third tilt only.""",default=-1)

	parser.add_argument("--subtractbackground",action='store_true',default=False,help="""
		This will extract a box from the tomogram much larger than the subtomogram.
		Projections will be generated. You MUST provide --tomogram for this.""")

	parser.add_argument("--normproc",type=str,help="""Not used anywhere yet. Default=None""", default='None')
	
	parser.add_argument("--thresh",type=str,help="""Not used anywhere yet. Default=None""", default='None')

	parser.add_argument("--yshort",action='store_true',help="""Not used anywhere yet. Default=False""", default=False)


	(options, args) = parser.parse_args()
	logger = E2init(sys.argv, options.ppid)
	
	if options.thresh == 'None' or options.thresh == 'none':
		options.thresh = None
	
	if options.normproc == 'None' or options.normproc == 'none':
		options.normproc = None
		
	from e2spt_classaverage import sptmakepath
	
	options = sptmakepath(options,'sptSubtilt')
	
	print "I've read the options"	
	
	#def subtiltextractor(parameters):
	
	if not options.tiltseries or not options.tiltangles or not options.coords:
		print "ERROR: You must provide ALL of the following options: --tiltseries, --tiltangles, --coords and --tomogramthickness."
		sys.exit()
	

	
	#k=-1
	#name = options.output
	
	serieshdr = EMData(options.tiltseries,0,True)
	nslices = serieshdr['nz']
	nx = serieshdr['nx']
	ny = serieshdr['ny']
	
	anglesfile = open(options.tiltangles,'r')				#Open tilt angles file
	alines = anglesfile.readlines()							#Read its lines
	anglesfile.close()										#Close the file
	
	tiltangles = [ alines[i].replace('\n','') for i in range(len(alines)) ]	#Eliminate trailing return character, '\n', for each line in the tiltangles file
	
	#for i in range(len(alines)):
	#	alines[i]=alines[i].replace('\n')					#Eliminate
	
	ntiltangles = len(tiltangles)
	
	if int(nslices) != int(ntiltangles):
		print """ERROR: The tiltangles file doesn't seem to correspond to the tiltseries provided.
				The number of images in --tiltseries (z dimension of MRC stack) must be equal to the number
				of lines in --tiltangles."""
		sys.exit()
	
	
	#"""
	#You do not need to keep track of the mathematics of tilting and rotating and find the correspondence between
	#tomogram and each image in the tilt series.
	#Instead, let's make a simple 3D model, containing a bright dot at the position of each particle.
	#Then, rotate that using the known tilt angles, generate a projection for each, and find the dots (maxima) in each.
	#Use the location of these maxima, to extract each particle from each image in the tilt series.
	#"""
	
	if options.tomosides:							#Read tomogram dimensions.
		sides=options.tomosides.split(',')
		tomox = int(sides[0])
		tomoy = int(sides[1])
		tomoz = int(sides[2])
	
	if options.tomogram:
		tomohdr = EMData(options.tomogram,0,True)	#Read tomogram dimensions from tomogram header, if the tomogram is provided.
		tomox = int(tomohdr['nx'])
		tomoy = int(tomohdr['ny'])
		tomoz = int(tomohdr['nz'])

	#if float( options.shrink ) > 1.0:								#The 'MODEL' to build for the coordinates need not use the full size of the tomogram.
	#	tomox = int(tomox)/options.shrink
	#	tomoy = int(tomoy)/options.shrink
	#	tomoz = int(tomoz)/options.shrink
	
	#tomovol = EMData(tomox,tomoy,tomoz)				#Create empty volume for the MODEL to build
	#tomovol.to_zero()								#Make sure it's empty
	
	cfile = open(options.coords,'r')				#Open coordinates file
	clines = cfile.readlines()						#Read its lines
	cfile.close()									#Close the file
	
	'''
	"Clean the coordinate files lines (clines) if there's garbage in them.
	Some people might manually make ABERRANT coordinates files with commas, tabs, or more than once space in between coordinates.
	Each line needs to be parsed.
	'''
	
	ptclNum=0
	
	cleanlines=[]
	for line in clines:
		
		if options.subset:
			if int(ptclNum) >= (options.subset):
				break
			
		line =line.replace(", ",' ')	
		line = line.replace(",",' ')
		line = line.replace("x",'')
		line = line.replace("y",'')
		line = line.replace("z",'')
		line = line.replace("=",'')
		line = line.replace("_",' ')
		line = line.replace("\n",'')
		line = line.replace("\t",' ')
		line = line.replace("  ",' ')
		
		finallineelements=line.split(' ')


		if line and len(finallineelements) ==3:
			cleanlines.append(line)
			ptclNum += 1
		else:
			print "\nBad line removed", line
	
	ptclNum=0		
	'''
	Iterate over the correct number of viable lines from the coordinates file.
	'''
	
	nptcls=len(cleanlines)
	if int(options.subset) > 0:
		if int(options.subset) > len(cleanlines):
			print """WARNING: The total amount of lines in the coordinates files is LESS than the subset of particles to box you specified; 
							therefore, ALL particles will be extracted."""
		else:
			nptcls - int(options.subset)
			print "The SUBSET of particles to work with is", nptcls
	else:
		print "The size of the ENTIRE SET of sub-tiltseries to extract is", nptcls

	
	print "There are these many clean lines", len(cleanlines)
	print "Clean lines are", cleanlines
	
	everyotherfactor = 1
	if options.everyother > 1:
		everyotherfactor = options.everyother
	
	
	maxtilt=0
	if options.subtractbackground:
		tiltanglesfloat = [ math.fabs( float( alines[i].replace('\n','') ) ) for i in range(len(alines)) ]
		maxtilt = max( tiltanglesfloat )
		print "\n(e2spt_subtilt.py) maxtilt is", maxtilt
		
		from e2spt_boxer import unbinned_extractor
		
		bgboxsize = (2 * options.boxsize / math.cos( math.radians(maxtilt+5)  )) + 10
		invert=0
		center=0
	
	
	
	for line in cleanlines:
	
		line = line.split()	
		
		if len(line) == 3:
			xc = float(line[0])				#Determine x y z coordinates for each line
			yc = float(line[1])
			zc = float(line[2])	
			print "\n\n\n\n\n+=================\nAnalyzing particle number+================\n", ptclNum
			print "\nRead these coordinates", xc,yc,zc
		else:
			print "\nThere's an aberrant line in your file, see", line
			sys.exit()
		
		
		if options.cshrink:
			xc*=options.cshrink
			yc*=options.cshrink
			zc*=options.cshrink
			
			print "\nThe real coordinates after multiplying cshrink are", xc,yc,zc
		
		outIndx=0
		ret=0
		wholebox=0
		
		for k in range(len(tiltangles)):
		
			
			if k % everyotherfactor:
				print "\nSkipping tilt",k
					
			else:
				
				angle = float( tiltangles[k] )
				#print "\n\n\nTilt %d, ANGLE %f" %( k, angle )
				#print "XC", xc
				tAxisShift = tomox/2.0
				#print "tAxisShift is", tAxisShift
				xcToAxis = xc - tAxisShift
				#print "Therefore, xcToAxis is", xcToAxis
				#if k==0:
				#	print "\nThe tilt axis goes through the middle, so xcoordinates need to be shifted by", xcshift
			
				#print "\nTilt axis shift (should be constant; first time applied it is negative", -tAxisShift
				#print "Because TOMOX is", tomox
				#print "Therefore, XC with respect TO tilt AXIS is", xcToAxis
				#print "\n\nZC", zc
				zSectionShift = tomoz/2.0
				#print "zSectionShift", zSectionShift
				zcToMidSection = zc - zSectionShift
				#print "zcToMidSection",zcToMidSection
			
				#print "ZC (constant)", zc
				#print "Therefore zSectionShift is", zSectionShift
				#print "Therefore, zcToMidSection", zcToMidSection
			
				#RY = math.array( [ [math.cos(tilt),0, -1 * math.sin(tilt), 0], [0,1,0,0], [math.sin(tilt), 0, math.cos(tilt), 0], [0,0,0,1] ] )
				#zt = zc* math.cos(tiltangles[k]) - xcshift * math.sin(tiltangles[k])
				
				
			
				
				#print "sin(angle)", math.sin( math.radians(angle) )
				#print "cos(angle)", math.cos( math.radians(angle) )
				
				cosTerm=xcToAxis * math.cos( math.radians(angle)  )
				sinTerm=zcToMidSection * math.sin( math.radians(angle)  )
				
				#print "Cos term is", cosTerm
				#print "Sin term is", sinTerm
				
				xtToAxis = zcToMidSection * math.sin( math.radians(angle)  ) + xcToAxis * math.cos( math.radians(angle)  )
				
				#print "Therefore the NEW coordinate is", xtToAxis
				
				#print "math.sin(angle) is", math.sin(angle)
				#print "math.cos(angle) is", math.cos(angle)
			
				#print "\nTherefore, the TILTED X respect TO AXIS is", xtToAxis
				
				yt = yc
				
				#print "yt,yc", yt,yc
				
				xt = xtToAxis + tAxisShift
				#print "The new corrected coordinate is", xt
			
				#zt = zcToMidSection + zSectionShift
			
				#print "\nHowever, after +tAxisShift, XT is", xt
				##print "\n\n@@@@@@@@@\nTherefore the final coordinates of the tilt view to extract in 2D are xt,yt", xt,yt
				#print "\n\n"
			
				if float(xt) < 0.0:
					print "Something went awfully wrong; you have a negative X coordinate",xt
					print "tomox and tomox/2.0 are", tomox,tomox/2.0
				
				if float(yt) < 0.0:
					print "Something went awfully wrong; you have a negative Y coordinate",yt
					print "yc is", yc
				
				if float(xt) < 0.0 or float(yt) < 0.0:
					print "Either X or Y are negative, see", xt, yt
					sys.exit()
				
				if float(xt) < float(options.boxsize)/2.0 or float(yt) < float(options.boxsize)/2.0:
					print "Pick a smaller boxsize; otherwise, some of your particles will contain empty regions outside the image"
					print "Particle is centered at", xt,yt
					print "And boxsize/2 is", options.boxsize/2.0
					sys.exit()
				
				r = Region( (2*xt-options.boxsize)/2, (2*yt-options.boxsize)/2, k, options.boxsize, options.boxsize, 1)
				print "\n\n\nRRRRRRRRRR\nThe region to extract is", r
				
				
				
				print "\n(e2spt_subtilt.py) Extracting image for tilt angle", angle
				e = EMData()
				e.read_image(options.tiltseries,0,False,r)
				#print "After reading it, nz is", e['nz']
				e['tiltAngle']=angle
				e['xt']=xt
				e['yt']=yt
				e['origin_x']=e['nx']/2.0
				e['origin_y']=e['ny']/2.0
				e['origin_z']=0
				
				if int( options.shrink ) > 1:
					e.process_inplace('math.meanshrink',{'n':options.shrink})
				
				#print "After shrinking, nz is", e['nz']
				#e.process_inplace('normalize')
			
				#print "I've read the 2D particle into the region, resulting in type", type(e)
				#print "The mean and sigma are", e['mean'], e['sigma']
				
				e.process_inplace('normalize')
				e.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '.hdf',outIndx)
				if k==0:
					e.write_image(options.path + 'prj0.hdf',0)
				
				if options.subtractbackground and maxtilt:
					
					"""
					rbg =  Region( (2*xt-bgboxsize)/2, (2*yt-bgboxsize)/2, k, bgboxsize, bgboxsize, 1)
					ebg = EMData()
					ebg.read_image(options.tiltseries,0,False,rbg)
					ebg['tiltAngle']=angle
					ebg['xt']=xt
					ebg['yt']=yt
					ebg['origin_x']=ebg['nx']/2.0
					ebg['origin_y']=ebg['ny']/2.0
					ebg['origin_z']=0
					
					print "(e2spt_subtilt.py) Extracted larger image for tilt angle " + str(angle) + " and mean " + str(ebg['mean']) + " for particle " + str(ptclNum)
					
					
					if float( options.shrink ) > 1.0:
						ebg.process_inplace('math.meanshrink',{'n':options.shrink})
						
					ebg.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_whole.hdf',outIndx)
					"""
									
					'''
					Extract a large volume around each particle (only for k==0), to distinguish ptcl from background
					and generate background-substracted re-projections (for each tilt angle)
					'''
					if k == 0:			
						#ret = unbinned_extractor(options,bgboxsize,xc,yc,zc,options.cshrink,invert,center,options.tomogram)
						rw =  Region( (2*xc-bgboxsize)/2, (2*yc-bgboxsize)/2, (2*zc-bgboxsize)/2, bgboxsize, bgboxsize, bgboxsize)
						
						wholebox = EMData()
						wholebox.to_zero()
						wholebox.read_image(options.tomogram,0,False,rw)
						
						if int( options.shrink ) > 1:
							wholebox.process_inplace('math.meanshrink',{'n':options.shrink})
						
						#wholebox.process_inplace('normalize.edgemean')
						
						print "(e2spt_subtilt.py) Extracted whole 3D box " + str(angle) + " and mean " + str(wholebox['mean']) + " for particle " + str(ptclNum)
						wholebox.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_whole3D.hdf',0)

					if wholebox:
						
						#e.process_inplace('normalize')
						
						'''
						Rotate the larger box extracted and then clip into prism
						to avoid density gradient (a rotated cube rotates the data inside)
						causing higher density in projections along the diagonal of the cube
						'''
						#angle = angle *-1
						t= Transform({'type':'eman','az':90,'alt':angle,'phi':-90})
						#t= Transform({'type':'eman','az':90,'alt':angle})
						#t= Transform({'type':'eman','alt':angle})


						print "\nTransform to ROTATE volume is", t
						
						wholeboxRot = wholebox.copy()
						wholeboxRot.transform(t)
						
						finalbox = options.boxsize
						finalbgbox = bgboxsize
						if int( options.shrink ) > 1:
							finalbox = options.boxsize / options.shrink
							finalbgbox = bgboxsize / options.shrink
											
						rbgprism =  Region( (wholebox['nx'] - finalbox)/2, (wholebox['ny'] - finalbox)/2, (wholebox['nz'] - finalbgbox)/2, finalbox, finalbox, finalbgbox)
						wholeboxRot.clip_inplace( rbgprism )
						print "\nSizes of prism are", wholeboxRot['nx'],wholeboxRot['ny'],wholeboxRot['nz']
						
						if k == 0 :
							wholeboxRot.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_whole3DROT.hdf',0)
						
						ptclreprj = wholeboxRot.project("standard",Transform())
						print "\nGenerated ptclreprj with mean and XY sizes", ptclreprj['mean'],type(ptclreprj), ptclreprj['nx'],ptclreprj['ny'],ptclreprj['nz']
						
						ptclreprj.mult( math.cos( math.radians(angle) ) )
						ptclreprj.process_inplace('normalize')
						
						if k==0:
							ptclreprj.write_image(options.path + 'reprj0nomatch.hdf',0)
						ptclreprj.process_inplace('filter.matchto',{'to':e})
						
						if k==0:
							ptclreprj.write_image(options.path + 'reprj0yesmatch.hdf',0)
						#ptclreprj.rotate(90,0,0)
						ptclreprj.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_reprj.hdf',outIndx)
					
						
						'''
						Generate projections of the background density by masking out the particle
						'''
						maskrad = finalbox/3.0
						
						bgbox = wholeboxRot.process('mask.sharp',{'inner_radius':maskrad})
												
						print "\nMasked bgbox with inner_radius, and ptclbox with outer_radius", maskrad
						
						bgprj = bgbox.project("standard",Transform())
						
						bgprj.mult( math.cos( math.radians(angle) ) )
						
						print "\nGenerated ptclreprj with mean and XY sizes", bgprj['mean'],type(bgprj), bgprj['nx'],bgprj['ny'],bgprj['nz']
						
						bgprj.process_inplace('normalize')
						
						
						bgprj.process_inplace('filter.matchto',{'to':e})
						bgprj.rotate(90,0,0)
						bgprj.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_bgprj.hdf',outIndx)
						
						clean = e - bgprj
						clean.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_clean.hdf',outIndx)
						print "\nComputed clean. Max e and Max bgprj are",e['maximum'], bgprj['maximum']
					
						cleanreprj = ptclreprj - bgprj
						print "\nComputed cleanprj"
						
						cleanreprj.write_image(options.path + '/subtiltPtcl_' + str(ptclNum) + '_cleanreprj.hdf',outIndx)
				
				outIndx+=1
						
				print "\n\n\n"
					
					
					
		
		#r = Region( (2*xm-box)/2, (2*ym-box)/2, 0, box, box,1)

					
		ptclNum+=1
		
		#		(cos q  0  -sin q   0)
		#Ry(q) = (0      1    0      0)
		#        (sin q  0  cos q    0)
		#        (0      0    0     1) 

		
		
		
	#	if float( options.shrink) > 1.0:					#Shrink them if the model will be smaller than the original tomgoram
	#		xc = xc/options.shrink
	#		yc = yc/options.shrink
	#		zc = zc/options.shrink
			
		#tomovol.set_value_at(xc,yc,zc,1)	#Set the value of the center pixel where any particles were picked to 1.
		
	
	#for tilt in tiltangles:
	#	t=Transform({'type':'eman','az':0,'phi':0,'alt':tilt})
	#	prj = tomovo.project('standard',t)
	#	
	#	for i in range(len(clines)):
	
	'''
	
	"""
	Old mathematical approach
	"""	
	for j in range(nslices):
		
		2Dregion = Region(0,0,j,nx,ny,j+1)
		#a = EMData(s)
		slice=EMData()
		slice.read_image(options.tiltseries,0,False,2Dregion)
		tiltaxisx = int(nx)/2
		
		alpha = tiltangles[j]
		#k = 1
		for i in range(nptcls):
			#Some people might manually make ABERRANT coordinates files with commas, tabs, or more than once space in between coordinates
			clines[i] = clines[i].replace(", ",' ')	
			clines[i] = clines[i].replace(",",' ')
			clines[i] = clines[i].replace("x",'')
			clines[i] = clines[i].replace("y",'')
			clines[i] = clines[i].replace("z",'')
			clines[i] = clines[i].replace("=",'')
			clines[i] = clines[i].replace("_",' ')
			clines[i] = clines[i].replace("\n",' ')
			clines[i] = clines[i].replace("\t",' ')
			clines[i] = clines[i].replace("  ",' ')
			clines[i] = clines[i].split()		
		
			xc = int(clines[i][0])
			yc = int(clines[i][1])
			zc = int(clines[i][2])
		
			y2 = y
			
			xp2ta = tiltaxisx - xc
			zp = zc - options.thickness/2
			
			if alpha > 0:
				zp = -1 * zp
			
			dxa = (xp2ta + zp) * cos(alpha)
			
			x2 = tiltaxis - la
			
			r = Region((x2 - boxsize)/2,(y2 - boxsize)/2, boxsize, boxsize)
        		e = EMData()
			e.read_image(s,0,False,r)
			
			name = 'particle#' + str(k).zfill(len(pcoords)) + '_slice' + str(j).zfill(len(pcoords)) + '.mrc'
	'''
		
if __name__ == '__main__':
	
	main()

#!/usr/bin/env python

#
# Author: David Woolford, 09/13/2007 (woolford@bcm.edu)
# Copyright (c) 2000-2007 Baylor College of Medicine
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
#
#

from EMAN2 import *
from optparse import OptionParser
from math import *
from copy import copy
import os
import sys

READ_HEADER_ONLY = True

def main():
	progname = os.path.basename(sys.argv[0])
	usage = """%prog [options] <input particles> <sim mx> <output>
	Produces class averages """
	parser = OptionParser(usage=usage,version=EMANVERSION)

	parser.add_option("--iter", type="int", help="The number of iterations to perform. Default is 1.", default=1)
	parser.add_option("--ref", type="string", help="The image name of the associated projections or classes that were used to for the classification (calculated by e2classify.py). If specified, similarity scores are calculated in the first iteration and used to cull bad particles. If not specified, all particles are including in the first class average.", default="")
	parser.add_option("--align",type="string",help="If doing more than one iteration, this is the name and parameters of the 'aligner' used to align particles to the previous class average. See \'e2help.py aligners\'. And example is \'--align=translational:maxshift=2\'. Default is None.", default=None)
	parser.add_option("--aligncmp",type="string",help="If doing more than one iteration, this is the name and parameters of the comparitor used by the fist stage aligner (specified with the \'--align\' argument) for determining the optimum alignment parameters. See \'e2help.py cmp\'. An example is \'--aligncmp=frc\'. Default is dot.",default="dot:normalize=1")
	parser.add_option("--ralign",type="string",help="Almost the same as the \'--align\' argument, this is the name and parameters of the second stage aligner which refines the results of the first alignment. Only applicable if doing more than one iteration. See \'e2help.py aligners\'. Typically the \'refine\' aligner is used. If this argument is not specified then no refinement of the alignment occurs. Default is None.", default=None)
	parser.add_option("--raligncmp",type="string",help="The name and parameters of the comparitor used by the second stage (\'--ralign\') aligner. See \'e2help.py cmp\'. An example is \'--raligncmp=phase\'. Default is dot.",default="dot:normalize=1")
	parser.add_option("--averager",type="string",help="Name and parameters of the averager used to generate the class average. See \'e2help.py averagers\'. An example is \'--averager=ctfcw\'. Default is \'image\'.",default="image")
	parser.add_option("--cmp",type="string",help="The name and parameters of the comparitor used to generate similarity scores, which is the basis of excluding particles from the class average. The similarity score is generated by comparing the aligned particle to the class average. See \'e2help.py cmp\'. An example is \'--cmp=SqEuclidean\'. Default is \'dot:normalize=1\'", default="dot:normalize=1")
	parser.add_option("--keep",type="float",help="The fraction of particles to keep in each class, based on the similarity score generated by the --cmp argument. Toggle the keepsig flag to change the keeping criterion from fraction-based to sigma-based. Particle exclusion is conservative, meaning if keep is 0.94 and there are 10 particles in the class than none are excluded. In the same vein, if keep were 0.84 then only one particle would excluded etc. Default is 1.0.",default=1.0)
	parser.add_option("--keepsig", action="store_true", dest="keepsig", default=False, help="Change the keep (\'--keep\') criterion from fraction-based to sigma-based. In this approach all of the similarity scores are treated like a distribution. Scores at one extreme of the distribution are the best scores, scores at the other end of the distribution are the worst. Thus, the middle of the distribution (the mean) does not represent the best score. Specifying a --keep value of 1 will exclude all particles with similarity scores further than 1 standard deviation from the mean. Default is off.")
	parser.add_option("--verbose","-v",action="store_true",help="Print useful information while the program is running. Default is off.",default=False)
	parser.add_option("--debug","-d",action="store_true",help="Print debugging infromation while the program is running. Default is off.",default=False)

	(options, args) = parser.parse_args()
		
	if len(args)<3 : parser.error("Input, classification matix, and output files required")

	if os.path.exists(args[2]):
		parser.error("File %s exists, will not write over, exiting" %args[2])

	# check to see if the image exists
	for i in range(0,2):
		if not os.path.exists(args[i]):
			parser.error("File %s does not exist" %args[i])
	
	if (options.iter < 1 ):
		parser.error("iter must be greater than or equal to 1" %options.proj)
		
	if (options.iter > 1 and options.align == None ):
		parser.error("If you iterate more than once the --align argument is needed")
		
	if (options.iter == 1 and options.align != None ):
		print "README - If you iterate only once you do not need to specify the --align argument. It has no effect."
	if (options.iter == 1 and options.ralign != None ):
		print "README - If you iterate only once you do not need to specify the --ralign argument. It has no effect."
	
	num_sim =  EMUtil.get_image_count(args[1])
	if ( num_sim != 5 ):
		print "Error expecting the classification matrix (image) to contain 5 images, got %d - please generate the similarity matrix using e2classify.py" %num_sim
		exit(1)
	
	(num_classes, num_part ) = gimme_image_2dimensions(args[1]);
	
	if (options.verbose):
		print "Classifications per particle %d, particles %d" %(num_classes, num_part)
	
	# classes contains the classifications - row is particle number, column data contains class numbers (could be greater than 1)
	classes = EMData()
	classes.read_image(args[1], 0)
	num_proj_required = classes.get_attr("maximum") 
	
	# double check that the argument reference image makes sense
	if (options.ref != ""):
		if not os.path.exists(options.ref):
			parser.error("File %s does not exist" %options.ref)
			
		num_ref= EMUtil.get_image_count(options.ref)
		if ( num_proj_required > num_ref ):
			print "Error, the classification matrix refers to a class number (%d) that is beyond the number of images (%d) in the reference image (%s)." %(num_proj_required,num_ref,options.ref)
			exit(1)
	
	# double check that the number of particles in the particle image matches the rows in the classification matrix (image)
	num_part_check =  EMUtil.get_image_count(args[0])
	if ( num_part != num_part_check ):
		print "Error, the number of rows (%d) in the classification matrix (image) does not match the number of particles (%d) in the input image." %(num_part,num_part_check)
		exit(1)
		
		
	options.align=parsemodopt(options.align)
	options.alicmp=parsemodopt(options.aligncmp)
	# note the parsing of the options.ralign parameters is left for later
	options.alircmp=parsemodopt(options.raligncmp)
	options.cmp=parsemodopt(options.cmp)
	
	# weights contains the weighting of the classification scheme stored in the EMData object "classes" - above
	# row is particle number, column data contains weights - rows should add to 1, but this is not checked.
	weights = EMData()
	weights.read_image(args[1], 1)
	# dx contains the x translation of the alignment
	# row is particle number, column is class idx (to class number stored in classes)
	dx = EMData()
	dx.read_image(args[1],2)
	# dy contains the y translation of the alignment
	# row is particle number, column is class idx (to class number stored in classes)
	dy = EMData()
	dy.read_image(args[1],3)
	# da contains is the azimuthal rotation of the alignment
	# row is particle number, column is class idx (to class number stored in classes)
	da = EMData()
	da.read_image(args[1],4)
	
	
	classification = {}
	for i in range(num_part):
		for j in range(num_classes):
			try: classification[classes.get_value_at(j,i)].append([i,weights.get_value_at(j,i),0,dx.get_value_at(j,i),dy.get_value_at(j,i), da.get_value_at(j,i)])
			except: classification[classes.get_value_at(j,i)] = [[i,weights.get_value_at(j,i),0,dx.get_value_at(j,i),dy.get_value_at(j,i), da.get_value_at(j,i)]]
	
	#if (options.debug):
		#for i in classification.items():
			#print "class %d has %d particles" %(i[0], len(i[1]))

	classes = {}
	
	for it in range(1,options.iter+1):

		#two temp EMData objects used at various locations below
		tmp1 = EMData()
		tmp2 = EMData()
		
		################################################################################
		# OVERSEE THE GENERATION AND STORAGE OF THE QUALITY METRIC, AND POTENTIAL ALIGNMENT
		################################################################################
		
		if (it == 1):
			# if this is the first iteration, and the user has specified the reference image
			# then we calculate the quality metric. This is used to exclude particles from the
			# class average.
			if (options.ref != "" ):
				if options.verbose: 
					print "Generating similarity metrics using reference images, iteration %d" %it
				for i in classification.items():
					if options.verbose: 
						print "%d/%d\r"%(i[0],num_proj_required),
						sys.stdout.flush()
					for j in i[1]:
						t3d = Transform3D(EULER_EMAN,j[5],0,0)
						t3d.set_posttrans(j[3], j[4])
						tmp1.read_image(args[0], j[0])
						tmp1.rotate_translate(t3d)
						
						tmp2.read_image(options.ref, int(i[0]))
						
						# Generate the quality metric using the reference image
						j[2] = tmp2.cmp(options.cmp[0],tmp1,options.cmp[1])
			
			if (options.debug):
				if (options.ref != "" ): print "Used reference to generate quality metrics on the first round"
				else: print "Did not generate quality metrics in the first round"
		else:
			# if this is not the first iteration we compare the particles to the class average
			# that was generated in the previous iteration to generate the quality metric, which
			# is then used to exclude particles from the next class average. This includes
			# an alignment step which can take time...
			if options.verbose: 
				print "Performing alignment to previous class average, generating similarity metrics, iteration %d" %it
			for i in classification.items():
				if options.verbose: 
					print "%d/%d\r"%(i[0],num_proj_required),
					sys.stdout.flush()
				for j in i[1]:
					tmp1.read_image(args[0], j[0])
					tmp2 = classes[i[0]]
					# Align the particle to its class average
					ta=tmp1.align(options.align[0],tmp2,options.align[1],options.alicmp[0],options.alicmp[1])
					
					
					#print "A Refine parms were %f %f %f" %(ta.get_attr_default("align.dx",0),ta.get_attr_default("align.dy",0),ta.get_attr_default("align.az",0))
					
					if ( options.ralign != None ):
						refineparms=parsemodopt(options.ralign)
						
						refineparms[1]["az"] = ta.get_attr_default("align.az",0)-1
						refineparms[1]["dx"] = ta.get_attr_default("align.dx",0)-1
						refineparms[1]["dy"] = ta.get_attr_default("align.dy",0)-1
						#refineparms[1]["mode"] = 0
						#refineparms[1]["rangex"] = 2
						#refineparms[1]["rangey"] = 2
						#refineparms[1]["rangeaz"] = 2
						#print refineparms[1]
						
						ta = tmp1.align(refineparms[0],tmp2,refineparms[1],options.alircmp[0],options.alircmp[1])
					
						#print "done ref alignment"
					#print "B Refine parms were %f %f %f" %(ta.get_attr_default("align.dx",0),ta.get_attr_default("align.dy",0),ta.get_attr_default("align.az",0))
					# Store the quality metric and alignment parameters
					# Note that ta could be the image aligned by the normal aligner, or the refine aligner,
					# depending on the program arguments
					j[2] = ta.cmp(options.cmp[0],tmp2,options.cmp[1])
					j[3] = ta.get_attr_default("align.dx",0)
					j[4] = ta.get_attr_default("align.dy",0)
					j[5] = ta.get_attr_default("align.az",0)
					
			if (options.verbose):
				if ( options.ralign != "" ): print "Performed refinement alignment"
				else :  print "Did not perform refinement alignment"

		################################################################################
		# OVERSEE THE CALCULATION OF THE QUALITY METRIC THRESHOLD
		################################################################################
		# Should quality scores be calculated...?
		do_qual = True
		# Only if not the following
		if ( it == 1 and options.ref == "" ): do_qual = False
		
		# Should the quality threshold be calculated?
		do_thresh = True
		# Only if not the following...
		if ( options.keepsig == False and options.keep == 1.0 ): do_thresh = False
		
		qual_scores = {}
		threshold = {}
		
		if do_qual and do_thresh:
			if options.verbose: 
				print "Calculating the similarity threshold, iteration %d" %it
			# Note the the results of a comparitor are generated such that 
			# smaller numbers are always better. E.G. If the comparison was based
			# on FRC the comparitor would multiply its results by negative one.
			# This enables the calculation of the quality metric threshold (here)
			# to be uniform
			for i in classification.items():
				for j in i[1]:
					try: qual_scores[i[0]].append(j[2])
					except: qual_scores[i[0]] = [j[2]]
		
			for i in qual_scores.items():
				if ( options.keepsig == True ):
					a = Util.get_stats_cstyle(i[1])
					mean = a["mean"]
					std_dev = a["std_dev"]
					threshold[i[0]] = [mean + options.keep*std_dev]
				else:
					b = copy(i[1])
					b.sort()
					# The ceil reflects a conservative policy. If the user specified keep=0.93
					# and there were 10 particles, then they would all be kept. If floor were
					# used instead of ceil, the last particle would be thrown away (in the
					# class average)
					idx = int(ceil(options.keep*len(b))-1)
					threshold[i[0]] = [b[idx]]
		
		if (options.debug):
			if ( do_qual and do_thresh ): print "Performed quality metric threshold calculation"
			else :  print " Did not perform quality metric threshold calculation"
		
		################################################################################
		# OVERSEE THE GENERATION OF THE CLASS AVERAGE
		################################################################################
		if options.verbose: 
			print "Averaging classes, iteration %d" %it
			
		for i in classification.items():
			if options.verbose: 
				print "%d/%d\r"%(i[0],num_proj_required),
				sys.stdout.flush()
	
			# Get the averager, this will calculate the class average.
			averager_parms=parsemodopt(options.averager)
			averager=Averagers.get(averager_parms[0], averager_parms[1])
		
			weight_sum = 0.0
			ptcl_repr = 0
			
			for j in i[1]:
				
				# impose the fraction-based or sigma-based culling of the particles in the class average
				# see arguments --keep and --keepsig
				if ( do_thresh and do_qual):
					if ( do_thresh and j[2] > threshold[i[0]][0] ): continue
				
				weight_sum += j[1]
				ptcl_repr += 1
				
				# Position the image correctly
				t3d = Transform3D(EULER_EMAN,j[5],0,0)
				t3d.set_posttrans(j[3], j[4])
				tmp1.read_image(args[0], j[0])
				tmp1.rotate_translate(t3d)
				
				# Add the image to the averager
				averager.add_image(tmp1)
	
			
			if ( weight_sum != 0 ):
				#Accomodate for non uniform weighting of particles in the class
				if (weight_sum != 1 ): averager.mult(1.0/weight_sum)
			
			if ( ptcl_repr != 0 ):
				# store the class to be used for comparison in the next iteration, or
				# for writing the output
				classes[i[0]] = averager.finish()
				classes[i[0]].set_attr("ptcl_repr", ptcl_repr)
	
	################################################################################
	# WRITE THE OUTPUT
	################################################################################
	tmp3 = EMData()
	if options.verbose: 
		print "Writing %s" %args[2]
	for i in classes.items():
		if ( options.ref != "" ):
			tmp3.read_image(options.ref, int(i[0]), READ_HEADER_ONLY)
			alt = tmp3.get_attr("euler_alt")
			az = tmp3.get_attr("euler_az")
			ph = tmp3.get_attr("euler_phi")
			i[1].set_rotation(az,alt,ph)
		
		i[1].write_image(args[2],-1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python
#
#  10/25/2015
#  New version.
#  
from sparx import *
import os
import global_def
from   global_def import *
from   optparse  import OptionParser
import sys
from   numpy     import array
import types
from   logger    import Logger, BaseLogger_Files
from morphology import 	get_shrink_3dmask



def sample_down_1D_curve(nxinit, nnxo, pspcurv_nnxo_file):
	shrinkage=float(nnxo)/float(nxinit)
	curv_orgn = read_text_file(pspcurv_nnxo_file)
	new_curv=int(1.5*len(curv_orgn))*[0.0]
	for index in xrange(len(curv_orgn)):
		new_index = int(index/shrinkage)
		fraction  =  index/shrinkage-new_index
		if fraction <=0:
			new_curv[new_index] +=curv_orgn[index]
		else:
			new_curv[new_index]  +=(1.-fraction)*curv_orgn[index]
			new_curv[new_index+1] += fraction*curv_orgn[index]
	return new_curv
	
def margin_of_error(P,size_of_this_sampling):
	# margin of an error, or radius of an error for a percentage
	from math import sqrt
	return sqrt(P*(1.-P)/size_of_this_sampling)
	
def get_margin_of_error(this_group_of_data,Tracker):
	ratio = margin_of_error(Tracker["P_chunk0"],len(this_group_of_data))
	rate1, rate2, size_of_this_sampling = count_chunk_members(Tracker["chunk_dict"],this_group_of_data)
	return abs(rate1-Tracker["P_chunk0"]),ratio,abs(rate2-Tracker["P_chunk1"]),ratio

def get_class_members(sort3d_dir):
	import os
	from utilities import read_text_file
	maximum_generations = 100
	maximum_groups      = 100
	class_list = []
	for igen in xrange(maximum_generations):
		gendir =os.path.join(sort3d_dir,"generation%03d"%igen)
		if os.path.exists(gendir):
			for igrp in xrange(maximum_groups):
				Class_file=os.path.join(gendir,"Kmref/Class%d.txt"%igrp)
				if os.path.exists(Class_file):
					class_one=read_text_file(Class_file)
					class_list.append(class_one)
				else:
					break
		else:
			break
	return class_list

def remove_small_groups(class_list,minimum_number_of_objects_in_a_group):
	new_class  = []
	final_list = []
	for one_class in class_list:
		if len(one_class)>=minimum_number_of_objects_in_a_group:
			new_class.append(one_class)  
			for element in one_class:
				final_list.append(element)
	final_list.sort()
	return final_list, new_class
	
def get_number_of_groups(total_particles,number_of_images_per_group):
	#minimum_number_of_members = 1000
	number_of_groups=float(total_particles)/number_of_images_per_group
	if number_of_groups - int(number_of_groups)<.4:number_of_groups = int(number_of_groups)
	else:number_of_groups = int(number_of_groups)+1
	return number_of_groups
	
def get_stable_members_from_two_runs(SORT3D_rootdirs,ad_hoc_number,log_main):
	#SORT3D_rootdirs                       =sys.argv[1]
	########
	from string import split
	sort3d_rootdir_list=split(SORT3D_rootdirs)
	dict1              =[]
	maximum_elements   = 0
	for index_sort3d in xrange(len(sort3d_rootdir_list)):
		sort3d_dir       = sort3d_rootdir_list[index_sort3d]
		all_groups       = get_class_members(sort3d_dir)
		dict1.append(all_groups)
		if maximum_elements <len(all_groups):
			maximum_elements = len(all_groups)
	TC =ad_hoc_number+1
	for indep in xrange(len(dict1)):
		alist=dict1[indep] 
		while len(alist)<maximum_elements:
			alist.append([TC])
			TC +=1
		dict1[indep]=alist
		TC +=1
	for a in dict1:log_main.add(len(a))
	dict = {}
	for index_sort3d in xrange(len(sort3d_rootdir_list)):
		sort3d_dir       = sort3d_rootdir_list[index_sort3d]
		dict[sort3d_dir] = dict1[index_sort3d]
	###### Conduct two-way comparison
	from numpy import array
	from statistics import k_means_match_clusters_asg_new
	for isort3d in xrange(0,1): #len(sort3d_rootdir_list)):
		li = dict[sort3d_rootdir_list[isort3d]]
		new_li = []
		for ili in xrange(len(li)):
			li[ili].sort()
			t= array(li[ili],'int32')
			new_li.append(t)
		avg_list = {}
		total    = {}
		for ii in xrange(len(li)):
			avg_list[ii]=0.0
			total[ii]=0.0
		for jsort3d in xrange(len(sort3d_rootdir_list)):
			if isort3d !=jsort3d:
				new_lj = []
				lj = dict[sort3d_rootdir_list[jsort3d]]
				for a in lj:
					log_main.add("the size is  %d"%len(a))
				for jlj in xrange(len(lj)):
					lj[jlj].sort()
					t= array(lj[jlj],'int32')
					new_lj.append(t)
				ptp=[new_li,new_lj]
				newindeces, list_stable, nb_tot_objs = k_means_match_clusters_asg_new(ptp[0],ptp[1])
				log_main.add("*************************************************************")
				log_main.add("the results of two P1 runs are: ")
				for index in xrange(len(newindeces)):
					log_main.add("  %d of %s matches  %d of %s"%(newindeces[index][0],sort3d_rootdir_list[isort3d],newindeces[index][1],sort3d_rootdir_list[jsort3d]))
				for index in xrange(len(list_stable)):
					log_main.add("%d   stable memebers"%len(list_stable[index]))
				#print newindeces, sort3d_rootdir_list[isort3d],sort3d_rootdir_list[jsort3d]
				#print "nb_tot_objs", nb_tot_objs/10001.*100.
				#print len(list_stable), len(newindeces)
				new_stable = []
				for ilist in xrange(len(list_stable)):
					if len(list_stable[ilist])!=0:
						new_stable.append(list_stable[ilist])
				for istable in xrange(len(new_stable)):
					stable = new_stable[istable]
					if len(stable)>0: 
						group_A =  li[newindeces[istable][0]]
						group_B =  lj[newindeces[istable][1]]
						#write_text_file(stable,"stable_%d_members%d.txt"%(jsort3d,istable))
						log_main.add(" %d %d %d   "%(len(group_A),len(group_B),len(stable)))
						#write_text_file(group_A,"stable_%d_members%d_group%d.txt"%(jsort3d,istable,newindeces[istable][0]))
						#write_text_file(group_B,"stable_%d_members%d_group%d.txt"%(jsort3d,istable,newindeces[istable][1]))
				#for index_of_matching in xrange(len(newindeces)):
				#	avg_list[newindeces[index_of_matching][0]] +=len(list_stable[newindeces[index_of_matching][0]])
				#	total[newindeces[index_of_matching][0]] += len(li[newindeces[index_of_matching][0]])#+len(lj[newindeces[index_of_matching][1]])
		return new_stable
		
def two_way_comparison_single(partition_A, partition_B,Tracker):
	###############
	from statistics import k_means_match_clusters_asg_new
	total_stack = Tracker["constants"]["total_stack"]
	log_main    = Tracker["constants"]["log_main"]
	myid        = Tracker["constants"]["myid"]
	main_node   = Tracker["constants"]["main_node"]
	numpy32_A = []
	numpy32_B = []
	total_A = 0
	total_B = 0
	if myid==main_node:
		log_main.add(" the first run has number of particles %d"%len(partition_A))
		log_main.add(" the second run has number of particles %d"%len(partition_B))
	for A in partition_A:
		total_A +=len(A)
	for B in partition_B:
		total_B +=len(B)
	nc_zero = 1
	if len(partition_A) < len(partition_B):
		while len(partition_A) <len(partition_B):
			partition_A.append([nc_zero+total_stack])
			nc_zero +=1
	elif len(partition_A) > len(partition_B):
		while len(partition_B) <len(partition_A):
			partition_B.append([nc_zero+total_stack])
			nc_zero +=1
	number_of_class=len(partition_A)
	for index_of_class in xrange(number_of_class):
		A = partition_A[index_of_class]
		A.sort()
		A= array(A,'int32')
		numpy32_A.append(A)
		B= partition_B[index_of_class]
		B.sort()
		B = array(B,'int32')
		numpy32_B.append(B)
		if myid ==main_node:
			log_main.add("group %d  %d   %d"%(index_of_class,len(A), len(B))) 
	ptp=[[],[]]
	ptp[0]=numpy32_A
	ptp[1]=numpy32_B
	newindexes, list_stable, nb_tot_objs = k_means_match_clusters_asg_new(ptp[0],ptp[1])
	if myid == main_node:
		log_main.add(" reproducible percentage of the first partition %f"%(nb_tot_objs/float(total_A)*100.))
		log_main.add(" reproducible percentage of the second partition %f"%(nb_tot_objs/float(total_B)*100.))
		for index in xrange(len(newindexes)):
			log_main.add("%d of A match %d of B "%(newindexes[index][0],newindexes[index][1]))
		for index in xrange(len(list_stable)):
			log_main.add("%d number of reproduced objects are found in group %d"%(len(list_stable[index]),index))
		log_main.add(" %d number of objects are reproduced "%nb_tot_objs)
		log_main.add(" margin of error")
	large_stable = []
	for index_of_stable in xrange(len(list_stable)):
		rate1,rate2,size_of_this_group = count_chunk_members(Tracker["chunk_dict"],list_stable[index_of_stable])
		if size_of_this_group>=Tracker["constants"]["smallest_group"]:
			error                          = margin_of_error(Tracker["P_chunk0"],size_of_this_group)
			if myid ==main_node:
				log_main.add(" chunk0  lower bound %f  upper bound  %f  for sample size  %d"%((Tracker["P_chunk0"]-error),(Tracker["P_chunk0"]+error),size_of_this_group))
				log_main.add(" actual percentage is %f"%rate1)
			large_stable.append(list_stable[index_of_stable])
		else:
			if myid==main_node:
				log_main.add("%d  group is too small"%index_of_stable)
	return large_stable
	
def get_leftover_from_stable(stable_list, N_total,smallest_group):
	tmp_dict={}
	for i in xrange(N_total):
		tmp_dict[i]=i
	new_stable =[]
	for alist in stable_list:
		if len(alist)>smallest_group:
			for index_of_list in xrange(len(alist)):
				del tmp_dict[alist[index_of_list]]
			new_stable.append(alist)
	leftover_list = []
	for one_element in tmp_dict:
		leftover_list.append(one_element)
	return leftover_list, new_stable

def get_initial_ID(part_list, full_ID_dict):
	part_initial_id_list = []
	new_dict = {}
	for iptl in xrange(len(part_list)):
		id = full_ID_dict[part_list[iptl]]
		part_initial_id_list.append(id)
		new_dict[iptl] = id
	return part_initial_id_list, new_dict
		
def Kmeans_exhaustive_run(ref_vol_list,Tracker):
	from applications import ali3d_mref_Kmeans_MPI
	import os
	from mpi import MPI_COMM_WORLD, mpi_barrier
	# npad is 2
	npad                  = 2
	myid                  = Tracker["constants"]["myid"]
	main_node             = Tracker["constants"]["main_node"]
	log_main              = Tracker["constants"]["log_main"]
	nproc                 = Tracker["constants"]["nproc"]
	final_list_text_file  = Tracker["this_data_list_file"]
	snr  =1.
	Tracker["total_stack"]= len(Tracker["this_data_list"])
	if myid ==main_node:
		log_main.add("start exhaustive Kmeans")
		log_main.add("total data is %d"%len(Tracker["this_data_list"]))
		log_main.add("final list file is "+final_list_text_file)
	workdir = Tracker["this_dir"]
	empty_group = 1
	kmref =0
	while empty_group ==1 and kmref<=5:
		if myid ==main_node:
			log_main.add(" %d     Kmref run"%kmref) 
		outdir =os.path.join(workdir, "Kmref%d"%kmref)
		empty_group, res_classes, data_list = ali3d_mref_Kmeans_MPI(ref_vol_list,outdir,final_list_text_file,Tracker)
		kmref +=1
		if empty_group ==1:
			if myid ==main_node:
				log_main.add("empty gorup appears, next round of Kmeans requires rebuilding reference volumes!")
				log_main.add(" the number of classes for next round before cleaning is %d"%len(res_classes))
			final_list   = []
			new_class    = []
			for a in res_classes:
				if len(a)>=Tracker["constants"]["smallest_group"]:
					for b in a:
						final_list.append(b)
					new_class.append(a)
			final_list.sort()
			Tracker["total_stack"]    = len(final_list)
			Tracker["this_data_list"] = final_list
			final_list_text_file = os.path.join(workdir, "final_list%d.txt"%kmref)
			if myid == main_node:
				log_main.add("number of classes for next round is %d"%len(new_class))
				write_text_file(final_list, final_list_text_file)
			mpi_barrier(MPI_COMM_WORLD)
			if myid == main_node:
				number_of_ref_class = []
				for igrp in xrange(len(new_class)):
					class_file =os.path.join(workdir,"final_class%d.txt"%igrp)
					write_text_file(new_class[igrp],class_file)
					number_of_ref_class.append(len(new_class[igrp]))
			else:
				number_of_ref_class = 0
			number_of_ref_class = wrap_mpi_bcast(number_of_ref_class,main_node)
			mpi_barrier(MPI_COMM_WORLD)
			ref_vol_list = []
			if  Tracker["constants"]["mask3D"]: mask3D = get_shrink_3dmask(Tracker["constants"]["nxinit"],Tracker["constants"]["mask3D"])
			else: mask3D =None
			Tracker["number_of_ref_class"] = number_of_ref_class
			for igrp in xrange(len(new_class)):
				class_file = os.path.join(workdir,"final_class%d.txt"%igrp)
				while not os.path.exists(class_file):
					#print  " my_id",myid
					sleep(2)
				mpi_barrier(MPI_COMM_WORLD)
				data,old_shifts = get_shrink_data_huang(Tracker,Tracker["nxinit"],class_file,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
				#volref = recons3d_4nn_ctf_MPI(myid=myid, prjlist = data, symmetry=Tracker["constants"]["sym"], finfo=None)
				#volref = filt_tanl(volref, Tracker["low_pass_filter"],.1)
				volref, fsc_kmref = rec3D_two_chunks_MPI(data,snr,Tracker["constants"]["sym"],mask3D,\
			 os.path.join(outdir, "resolution_%02d_Kmref%04d"%(igrp,kmref)),myid,main_node,index=-1,npad=npad,finfo=None)
				ref_vol_list.append(volref)
				mpi_barrier(MPI_COMM_WORLD)
		else:
			new_class    = []
			for a in res_classes:
				if len(a)>=Tracker["constants"]["smallest_group"]:new_class.append(a)
	if myid==main_node:
		log_main.add("Exhaustive Kmeans ends")
		log_main.add(" %d groups are selected out"%len(new_class))
	return new_class 
	
def print_upper_triangular_matrix(data_table_dict,N_indep,log_main):
		msg =""
		for i in xrange(N_indep):
			msg +="%7d"%i
		log_main.add(msg)
		for i in xrange(N_indep):
			msg ="%5d "%i
			for j in xrange(N_indep):
				if i<j:
					msg +="%5.2f "%data_table_dict[(i,j)]
				else:
					msg +="      "
			log_main.add(msg)
			
def print_a_line_with_timestamp(string_to_be_printed ):                 
	line = strftime("%Y-%m-%d_%H:%M:%S", localtime()) + " =>"
 	print(line,string_to_be_printed)
	return string_to_be_printed

def convertasi(asig,K):
	p=[]
	for k in xrange(K):
		l = []
		for i in xrange(len(asig)):
			if asig[i]==k: l.append(i)
		l=array(l,"int32")
		l.sort()
		p.append(l)
	return p
	
def prepare_ptp(data_list,K):
	num_of_pt=len(data_list)
	ptp=[]
	for ipt in xrange(num_of_pt):
		ptp.append([])
	for ipt in xrange(num_of_pt):
		nc =len(data_list[ipt])
		asig=[-1]*nc
		for i in xrange(nc):
			asig[i]=data_list[ipt][i]
		ptp[ipt] = convertasi(asig,K)
	return ptp

def print_dict(dict,theme):
		line = strftime("%Y-%m-%d_%H:%M:%S", localtime()) + " =>"
		print(line+theme)
		spaces = "                           "
		for key, value in sorted( dict.items() ):
			if(key != "constants"):  
				print("                    => "+key+spaces[len(key):]+":  "+str(value))

def get_resolution_mrk01(vol, radi, nnxo, fscoutputdir, mask_option):
        # this function is single processor
        #  Get updated FSC curves, user can also provide a mask using radi variable
	import types
	from statistics import fsc
	from utilities import model_circle, get_im
	from filter import fit_tanh1
	if(type(radi) == int):
		if(mask_option is None):  mask = model_circle(radi,nnxo,nnxo,nnxo)
		else:                           mask = get_im(mask_option)
	else:  mask = radi
	nfsc = fsc(vol[0]*mask,vol[1]*mask,1.0,os.path.join(fscoutputdir,"fsc.txt") )
	currentres = -1.0
	ns = len(nfsc[1])
	#  This is actual resolution, as computed by 2*f/(1+f)
	for i in xrange(1,ns-1):
		if ( nfsc[1][i] < 0.333333333333333333333333):
			currentres = nfsc[0][i-1]
			break
		#if(currentres < 0.0):
			#print("  Something wrong with the resolution, cannot continue")
		currentres = nfsc[0][i-1]
        
        """ this commented previously
		lowpass = 0.5
		ns = len(nfsc[1])
        #  This is resolution used to filter half-volumes
        for i in xrange(1,ns-1):
                if ( nfsc[1][i] < 0.5 ):
                        lowpass = nfsc[0][i-1]
                        break
        """  
	lowpass, falloff = fit_tanh1(nfsc, 0.01)
	return  round(lowpass,4), round(falloff,4), round(currentres,2)
        
def partition_to_groups(partition_list,K):
	res =[]
	for igroup in xrange(K):
		this_group =[]
		for imeb in xrange(len(partition_list)):
			if partition_list[imeb] ==igroup:
				this_group.append(imeb)
		this_group.sort()
		res.append(this_group)
	return res

def partition_independent_runs(run_list,K):
	indep_runs_groups={}
	for indep in xrange(len(run_list)):
		this_run = run_list[indep]
		groups = partition_to_groups(this_run,K)
		indep_runs_groups[indep]=groups 
	return indep_runs_groups

def get_outliers(total_number,plist):
	tlist={}
	for i in xrange(total_number):
		tlist[i]=i
	for a in plist:
		del tlist[a]
	out =[]
	for a in tlist:
		out.append(a)
	return out

def merge_groups(stable_members_list,smallest_group):
	alist=[]
	for i in xrange(len(stable_members_list)):
		if len(stable_members_list[i])>=smallest_group:
			for j in xrange(len(stable_members_list[i])):
				alist.append(stable_members_list[i][j])
	return alist

def save_alist(Tracker,name_of_the_text_file,alist):
	from utilities import write_text_file
	import os
	log       =Tracker["constants"]["log_main"]
	myid      =Tracker["constants"]["myid"]
	main_node =Tracker["constants"]["main_node"]
	dir_to_save_list =Tracker["this_dir"]
	if myid==main_node:
		file_name=os.path.join(dir_to_save_list,name_of_the_text_file)
		write_text_file(alist, file_name)

def select_two_runs(summed_scores,two_way_dict):
	summed_scores.sort()
	rate1 = summed_scores[-1]
	rate2 = None
	for index in xrange(2,len(summed_scores)+1):
		rate2 =summed_scores[-index]
		if rate2 !=rate1:
			break
	if rate2 != None:
		if rate1 != rate2:
			tmp_run1= two_way_dict[rate1]
			tmp_run2= two_way_dict[rate2]
			run1 = min(tmp_run1,tmp_run2)
			run2 = max(tmp_run1,tmp_run2)
		else:
			run1 = 0
			run2 = 1
			rate2=rate1
	else:
		run1 =0
		run2 =1
		rate2 = rate1
	return run1, run2, rate1, rate2
	
def do_two_way_comparison(Tracker):
	from mpi import mpi_barrier, MPI_COMM_WORLD
	from utilities import read_text_file,write_text_file
	from statistics import k_means_match_clusters_asg_new
	######
	myid              =Tracker["constants"]["myid"]
	main_node         =Tracker["constants"]["main_node"]
	log_main          =Tracker["constants"]["log_main"]
	total_stack       =Tracker["this_total_stack"]
	workdir           =Tracker["this_dir"]
	number_of_groups  =Tracker["number_of_groups"]
	######
	if myid ==main_node:
		msg="-------Two_way comparisons analysis of %3d independent runs of equal Kmeans-------"%Tracker["constants"]["indep_runs"]
		log_main.add(msg)
	total_partition=[]
	if Tracker["constants"]["indep_runs"]<2:
		if myid ==main_node:
			log_main.add(" Error! One single run cannot make two-way comparison")
		from mip import mpi_finalize
		mpi_finalize()
		exit()
	for iter_indep in xrange(Tracker["constants"]["indep_runs"]):
		partition_list=Tracker["partition_dict"][iter_indep]
		total_partition.append(partition_list)
    ### Two-way comparision is carried out on all nodes 
	ptp=prepare_ptp(total_partition,number_of_groups)
	indep_runs_to_groups =partition_independent_runs(total_partition,number_of_groups)
	###### Check margin of error
	if myid ==main_node:
		log_main.add("--------------------------margin of error--------------------------------------------")
	for indep in xrange(len(indep_runs_to_groups)):
		for index_of_class in xrange(len(indep_runs_to_groups[indep])):
			one_group_in_old_ID,tmp_dict = get_initial_ID(indep_runs_to_groups[indep][index_of_class],Tracker["full_ID_dict"])
			rate1,rate2,size_of_this_group = count_chunk_members(Tracker["chunk_dict"],one_group_in_old_ID)
			error=margin_of_error(Tracker["P_chunk0"],size_of_this_group)
			if myid ==main_node:
				log_main.add(" chunk0  lower bound %f   upper bound  %f  for class  %d"%((Tracker["P_chunk0"]-error),(Tracker["P_chunk0"]+error),size_of_this_group))
				log_main.add(" actual percentage is %f"%rate1)
				#log_main.add(" margin of error for chunk1 is %f"%margin_of_error(Tracker["P_chunk1"],size_of_this_group))
				#log_main.add(" actual error is %f"%abs(rate2-Tracker["P_chunk1"]))
	if myid ==main_node:
		log_main.add("------------------------------------------------------------------------------")
	total_pop=0
	two_ways_stable_member_list={}
	avg_two_ways               =0.0
	avg_two_ways_square        =0.
	scores                     ={}
	for iptp in xrange(len(ptp)):
		for jptp in xrange(len(ptp)):
			newindeces, list_stable, nb_tot_objs = k_means_match_clusters_asg_new(ptp[iptp],ptp[jptp])
			tt =0.
			if myid ==main_node and iptp<jptp:
				aline="Two-way comparison between independent run %3d and %3d"%(iptp,jptp)
				log_main.add(aline)
			for m in xrange(len(list_stable)):
				a=list_stable[m]
				tt +=len(a)
				#if myid==main_node and iptp<jptp:
					#aline=print_a_line_with_timestamp("Group %d  number of stable members %10d  "%(m,len(a)))
					#log_main.add(aline)
					#aline=print_a_line_with_timestamp("The comparison is between %3d th group of %3d th run and %3d th group of %3d th run" \
					# 									%(newindeces[m][0],iptp,newindeces[m][1],jptp))
					#log_main.add(aline)
					#aline=print_a_line_with_timestamp("The  %3d th group of %3d th run contains %6d members" \
					#	        %(iptp,newindeces[m][0],len(indep_runs_to_groups[iptp][newindeces[m][0]])))
					#log_main.add(aline)
					#aline=print_a_line_with_timestamp("The  %3d th group of %3d th run contains %6d members"%(jptp,newindeces[m][1],\
					#			len(indep_runs_to_groups[jptp][newindeces[m][1]]))) 
			if myid==main_node and iptp<jptp:
				unaccounted=total_stack-tt
				ratio_unaccounted  = 100.-tt/total_stack*100.
				ratio_accounted    = tt/total_stack*100
				#aline             = print_a_line_with_timestamp("Accounted data is %6d, %5.2f "%(int(tt),ratio_accounted))
				#log_main.add(aline)
				#aline=print_a_line_with_timestamp("Unaccounted data is %6d, %5.2f"%(int(unaccounted),ratio_unaccounted))
				#log_main.add(aline)
			rate=tt/total_stack*100.0
			scores[(iptp,jptp)] =rate
			if iptp<jptp:
				avg_two_ways 	    +=rate
				avg_two_ways_square +=rate**2
				total_pop +=1
				#if myid ==main_node and iptp<jptp:
				#aline=print_a_line_with_timestamp("The two-way comparison stable member total ratio %3d %3d %5.3f  "%(iptp,jptp,rate))
				#log_main.add(aline)
				new_list=[]
				for any in list_stable:
					any.tolist()
					new_list.append(any)
				two_ways_stable_member_list[(iptp,jptp)]=new_list
	if myid ==main_node:
		log_main.add("two_way comparison is done!")
	#### Score each independent run by pairwise summation
	summed_scores =[]
	two_way_dict  ={}
	for ipp in xrange(len(ptp)):
		avg_scores =0.0
		for jpp in xrange(len(ptp)):
			if ipp!=jpp:
				avg_scores +=scores[(ipp,jpp)]
		avg_rate =avg_scores/(len(ptp)-1)
		summed_scores.append(avg_rate)
		two_way_dict[avg_rate] =ipp
	#### Select two independent runs that have the first two highest scores
	run1, run2,rate1,rate2 = select_two_runs(summed_scores,two_way_dict)
	Tracker["two_way_stable_member"]      = two_ways_stable_member_list[(run1,run2)]
	Tracker["pop_size_of_stable_members"] = 1
	if myid == main_node:
		log_main.add("extract outliers from the selected comparison")
	####  Save both accounted ones and unaccounted ones
	if myid == main_node:
		log_main.add("save the outliers")
	stable_class_list = []
	small_group_list  = []
	if myid ==main_node:
		log_main.add("------------------margin of error--------------------------------------------")
	for istable in xrange(len(Tracker["two_way_stable_member"])):
		one_class = Tracker["two_way_stable_member"][istable]
		#write_text_file(one_class, "class%d.txt"%istable)
		new_one_class, new_tmp_dict = get_initial_ID(one_class, Tracker["full_ID_dict"])
		#write_text_file(new_one_class, "new_class%d.txt"%istable)
		rate1, rate2, size_of_this_group = count_chunk_members(Tracker["chunk_dict"],new_one_class)
		error=margin_of_error(Tracker["P_chunk0"],size_of_this_group)
		if myid ==main_node:
			log_main.add(" margin of error for chunk0  lower bound %f   upper bound  %f  for sample size  %d"%((Tracker["P_chunk0"]-error),(Tracker["P_chunk0"]+error),size_of_this_group))
			log_main.add(" actual percentage is %f"%rate1)
			#log_main.add(" margin of error for chunk1 is %f"%margin_of_error(Tracker["P_chunk1"],size_of_this_group))
			#log_main.add(" actual error is %f"%abs(rate2-Tracker["P_chunk1"]))
		if len(new_one_class)>=Tracker["constants"]["smallest_group"]:
			stable_class_list.append(new_one_class) 
		else:
			small_group_list.append(new_one_class)
	if myid ==main_node:log_main.add("----------------------------------------------------------------------------")
	accounted_list = merge_groups(stable_class_list, Tracker["constants"]["smallest_group"])
	Tracker["this_accounted_list"]   =  accounted_list
	Tracker["two_way_stable_member"] =  stable_class_list
	outliers     = get_complementary_elements(Tracker["this_accounted_list"],accounted_list) 
	save_alist(Tracker,"Unaccounted.txt",outliers)
	Tracker["this_unaccounted_list"] =  outliers
	mpi_barrier(MPI_COMM_WORLD)
	save_alist(Tracker,"Accounted.txt",accounted_list)
	update_full_dict(accounted_list,Tracker)# Update full_ID_dict for Kmeans
	mpi_barrier(MPI_COMM_WORLD)
	Tracker["this_unaccounted_dir"]     =workdir
	Tracker["this_unaccounted_text"]    =os.path.join(workdir,"Unaccounted.txt")
	Tracker["this_accounted_text"]      =os.path.join(workdir,"Accounted.txt")
	Tracker["ali3d_of_outliers"]        =os.path.join(workdir,"ali3d_params_of_outliers.txt")
	Tracker["ali3d_of_accounted"]       =os.path.join(workdir,"ali3d_params_of_accounted.txt")
	if myid==main_node:
		log_main.add(" Selected indepedent runs      %5d and  %5d"%(run1,run2))
		log_main.add(" Their pair-wise averaged rates are %5.2f  and %5.2f "%(rate1,rate2))		
	from math import sqrt
	avg_two_ways = avg_two_ways/total_pop
	two_ways_std = sqrt(avg_two_ways_square/total_pop-avg_two_ways**2)
	net_rate     = avg_two_ways-1./number_of_groups*100.
	Tracker["net_rate"]=net_rate
	if myid ==main_node: 
		msg="average of two-way comparison  %5.3f"%avg_two_ways
		log_main.add(msg)
		msg="net rate of two-way comparison  %5.3f"%net_rate
		log_main.add(msg)
		msg="std of two-way comparison %5.3f"%two_ways_std
		log_main.add(msg)
		msg ="Score table of two_way comparison when Kgroup =  %5d"%number_of_groups
		log_main.add(msg)
		print_upper_triangular_matrix(scores,Tracker["constants"]["indep_runs"],log_main)
	del two_ways_stable_member_list
	Tracker["score_of_this_comparison"]=(avg_two_ways,two_ways_std,net_rate)
	mpi_barrier(MPI_COMM_WORLD)

	
def get_ali3d_params(ali3d_old_text_file,shuffled_list):
	from utilities import read_text_row
	ali3d_old = read_text_row(ali3d_old_text_file)
	ali3d_new = []
	for iptl in xrange(len(shuffled_list)):
		ali3d_new.append(ali3d_old[shuffled_list[iptl]])
	return ali3d_new

def counting_projections(delta,ali3d_params,image_start):
	from utilities import even_angles,angle_between_projections_directions
	sampled_directions = {}
	angles=even_angles(delta,0,180)
	for a in angles:
		[phi0, theta0, psi0]=a
		sampled_directions[(phi0,theta0)]=[]
	from math import sqrt
	for i in xrange(len(ali3d_params)):
		[phi, theta, psi, s2x, s2y] = ali3d_params[i]
		dis_min    = 9999.
		this_phi   = 9999.
		this_theta = 9999.
		this_psi   = 9999.
		prj1       =[phi,theta]
		for j in xrange(len(angles)):
			[phi0, theta0, psi0] = angles[j]
			prj2 =[phi0,theta0]
			dis=angle_between_projections_directions(prj1, prj2)
			if dis<dis_min:
				dis_min    =dis
				this_phi   =phi0
				this_theta =theta0
				this_psi   =psi0
		alist= sampled_directions[(this_phi,this_theta)]
		alist.append(i+image_start)
		sampled_directions[(this_phi,this_theta)]=alist
	return sampled_directions

def unload_dict(dict_angles):
	dlist =[]
	for a in dict_angles:
		tmp=[a[0],a[1]]
		tmp_list=dict_angles[a]
		for b in tmp_list:
			tmp.append(b)
		dlist.append(tmp)
	return dlist

def load_dict(dict_angle_main_node, unloaded_dict_angles):
	for ang_proj in unloaded_dict_angles:
		if len(ang_proj)>2:
			for item in xrange(2,len(ang_proj)):
				dict_angle_main_node[(ang_proj[0],ang_proj[1])].append(item)
	return dict_angle_main_node

def get_stat_proj(Tracker,delta,this_ali3d):
	from mpi import mpi_barrier, MPI_COMM_WORLD
	from utilities import read_text_row,wrap_mpi_bcast,even_angles
	from applications import MPI_start_end
	myid      = Tracker["constants"]["myid"]
	main_node = Tracker["constants"]["main_node"]
	nproc     = Tracker["constants"]["nproc"]
	mpi_comm  = MPI_COMM_WORLD
	if myid ==main_node:
		ali3d_params=read_text_row(this_ali3d)
		lpartids    = range(len(ali3d_params))
	else:
		lpartids      = 0
		ali3d_params  = 0
	lpartids = wrap_mpi_bcast(lpartids, main_node)
	ali3d_params = wrap_mpi_bcast(ali3d_params, main_node)
	ndata=len(ali3d_params)
	image_start, image_end = MPI_start_end(ndata, nproc, myid)
	ali3d_params=ali3d_params[image_start:image_end]
	sampled=counting_projections(delta,ali3d_params,image_start)
	for inode in xrange(nproc):
		if myid ==inode:
			dlist=unload_dict(sampled)
		else:
			dlist =0
		dlist=wrap_mpi_bcast(dlist,inode)
		if myid ==main_node and inode != main_node:
			sampled=load_dict(sampled,dlist)
		mpi_barrier(MPI_COMM_WORLD)
	return sampled

def get_attr_stack(data_stack,attr_string):
	attr_value_list = []
	for idat in xrange(len(data_stack)):
		attr_value = data_stack[idat].get_attr(attr_string)
		attr_value_list.append(attr_value)
	return attr_value_list

def fill_in_mpi_list(mpi_list,data_list,index_start,index_end):
	for index in xrange(index_start, index_end):
		mpi_list[index] = data_list[index-index_start]
	return mpi_list
	
def get_sorting_params(Tracker,data):
	from mpi import mpi_barrier, MPI_COMM_WORLD
	from utilities import read_text_row,wrap_mpi_bcast,even_angles
	from applications import MPI_start_end
	myid      = Tracker["constants"]["myid"]
	main_node = Tracker["constants"]["main_node"]
	nproc     = Tracker["constants"]["nproc"]
	ndata     = Tracker["total_stack"]
	mpi_comm  = MPI_COMM_WORLD
	if myid == main_node:
		total_attr_value_list = []
		for n in xrange(ndata):
			total_attr_value_list.append([])
	else:
		total_attr_value_list = 0
	for inode in xrange(nproc):
		attr_value_list =get_attr_stack(data,"group")
		attr_value_list =wrap_mpi_bcast(attr_value_list,inode)
		if myid ==main_node:
			image_start,image_end=MPI_start_end(ndata,nproc,inode)
			total_attr_value_list=fill_in_mpi_list(total_attr_value_list,attr_value_list,image_start,image_end)		
		mpi_barrier(MPI_COMM_WORLD)
	total_attr_value_list = wrap_mpi_bcast(total_attr_value_list,main_node)
	return total_attr_value_list

def get_ID_of_full_list(data_list, data_dict):
	data_in_full_list =[]
	for index in xrange(len(data_list)):
		data_dict[data_list[index]]=old_ID
		data_in_full_list.append(old_ID)
	return data_in_full_list
	
def create_random_list(Tracker):
	import random
	myid        = Tracker["constants"]["myid"]
	main_node   = Tracker["constants"]["main_node"]
	total_stack = Tracker["total_stack"]
	from utilities import wrap_mpi_bcast
	indep_list  =[]
	import copy
	SEED= Tracker["constants"]["seed"]
	if SEED ==-1:random.seed()
	else:random.seed(SEED)
	for irandom in xrange(Tracker["constants"]["indep_runs"]):
		ll=copy.copy(Tracker["this_data_list"])
		random.shuffle(ll)
		ll = wrap_mpi_bcast(ll, main_node)
		indep_list.append(ll)
	Tracker["this_indep_list"]=indep_list

def recons_mref(Tracker):
	from mpi import mpi_barrier, MPI_COMM_WORLD
	myid             = Tracker["constants"]["myid"]
	main_node        = Tracker["constants"]["main_node"]
	nproc            = Tracker["constants"]["nproc"]
	number_of_groups = Tracker["number_of_groups"]
	log_main         = Tracker["constants"]["log_main"]
	particle_list    = Tracker["this_particle_list"]
	nxinit           = Tracker["nxinit"]
	partstack        = Tracker["constants"]["partstack"]
	workdir          = Tracker["this_dir"]
	total_data       = len(particle_list)
	ref_list         = []
	number_of_ref_class = []
	for igrp in xrange(number_of_groups):
		a_group_list=particle_list[(total_data*igrp)//number_of_groups:(total_data*(igrp+1))//number_of_groups]
		a_group_list.sort()
		#Tracker["this_data_list"] = a_group_list
		from utilities import write_text_file
		particle_list_file = os.path.join(workdir,"iclass%d.txt"%igrp)
		if myid ==main_node:
			write_text_file(a_group_list,particle_list_file)
		mpi_barrier(MPI_COMM_WORLD)
		while not os.path.exists(particle_list_file):
			#print  " my_id",myid
			sleep(2)
			mpi_barrier(MPI_COMM_WORLD)
		data, old_shifts =  get_shrink_data_huang(Tracker,nxinit,particle_list_file,partstack,myid,main_node,nproc,preshift=True)
		#vol=reconstruct_3D(Tracker,data)
		mpi_barrier(MPI_COMM_WORLD)
		vol = recons3d_4nn_ctf_MPI(myid=myid,prjlist=data,symmetry=Tracker["constants"]["sym"],finfo=None)
		if myid ==main_node:log_main.add("reconstructed %3d"%igrp)
		ref_list.append(vol)
		number_of_ref_class.append(len(a_group_list))
	Tracker["number_of_ref_class"] =  number_of_ref_class
	return ref_list

def apply_low_pass_filter(refvol,Tracker):
	from filter import filt_tanl
	for iref in xrange(len(refvol)):
		refvol[iref]=filt_tanl(refvol[iref],Tracker["low_pass_filter"],.1)
	return refvol
	
def get_groups_from_partition(partition, initial_ID_list, number_of_groups):
	# sort out Kmref results to individual groups that has initial IDs
	# make a dictionary
	dict = {}
	for iptl in xrange(len(initial_ID_list)):
		dict[iptl] = initial_ID_list[iptl]
	res = []
	for igrp in xrange(number_of_groups):
		class_one = []
		for ipt in xrange(len(partition)):
			if partition[ipt] == igrp:
				orginal_id = dict[ipt]
				class_one.append(orginal_id)
		if len(class_one)>=1:
			res.append(class_one)
	return res

def get_complementary_elements(total_list,sub_data_list):
	if len(total_list)<len(sub_data_list):
		print "Wrong input list!"
		return []
	else:
		sub_data_dict     = {}
		complementary     = []
		for index in xrange(len(sub_data_list)):sub_data_dict[sub_data_list[index]]=index
		for any in total_list:
			if sub_data_dict.has_key(any) is False:complementary.append(any)
		return complementary

def get_complementary_elements_total(total_stack, data_list):
	data_dict    ={}
	complementary     = []
	for index in xrange(len(data_list)):data_dict[data_list[index]]=index
	for index in xrange(total_stack):
		if data_dict.has_key(index) is False:complementary.append(index)
	return complementary

def update_full_dict(leftover_list,Tracker):
	full_dict ={}
	for iptl in xrange(len(leftover_list)):
		full_dict[iptl]     = leftover_list[iptl]
	Tracker["full_ID_dict"] = full_dict
	
def split_a_group(workdir,list_of_a_group,Tracker):
	### Using EQ-Kmeans and Kmeans to split a group
	from utilities import wrap_mpi_bcast
	from random import shuffle
	from mpi import MPI_COMM_WORLD, mpi_barrier
	################
	myid        = Tracker["constants"]["myid"]
	main_node   = Tracker["constants"]["main_node"]
	nproc       = Tracker["constants"]["nproc"]
	total_stack = len(list_of_a_group)
	################
	import copy
	data_list = copy.deepcopy(list_of_a_group)
	update_full_dict(data_list,Tracker)
	this_particle_text_file = os.path.join(workdir,"full_class.txt")
	if myid ==main_node:
		write_text_file(data_list,"full_class.txt")
	# Compute the resolution of leftover 
	if myid ==main_node:
		shuffle(data_list)
		l1=data_list[0:total_stack//2]
		l2=data_list[total_stack//2:]
		l1.sort()
		l2.sort()
	else:
		l1 = 0
		l2 = 0
	l1 = wrap_mpi_bcast(l1, main_node)
	l2 = wrap_mpi_bcast(l2, main_node)
	llist = []
	llist.append(l1)
	llist.append(l2)
	if myid ==main_node:
		for index in xrange(2): 
			partids = os.path.join(workdir,"Class_%d.txt"%index)
			write_text_file(llist[index],partids)
	mpi_barrier(MPI_COMM_WORLD)
	################ create references for EQ-Kmeans
	ref_list = []
	for index in xrange(2):
		partids = os.path.join(workdir,"Class_%d.txt"%index)
		while not os.path.exists(partids):
			#print  " my_id",myid
			sleep(2)
		mpi_barrier(MPI_COMM_WORLD)
		data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nxinit"],partids,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
		vol = recons3d_4nn_ctf_MPI(myid=myid,prjlist = data,symmetry=Tracker["constants"]["sym"],finfo=None)
		vol = filt_tanl(vol,Tracker["constants"]["low_pass_filter"],.1)
		ref_list.append(vol)
	mpi_barrier(MPI_COMM_WORLD)
	### EQ-Kmeans
	outdir = os.path.join(workdir,"EQ-Kmeans")
	mref_ali3d_EQ_Kmeans(ref_list,outdir,this_particle_text_file,Tracker)
	res_EQ = partition_to_groups(Tracker["this_partition"],K=2)
	new_class = []
	for index in xrange(len(res_EQ)):
		new_ID, new_dict = get_initial_ID(res_EQ(index),Tracker["full_ID_dict"])
		new_class.append(new_ID)
		if myid ==main_node:
			new_class_file = os.path.join(workdir,"new_class%d.txt"%index)
			write_text_file(new_ID,new_class_file)
	mpi_barrier(MPI_COMM_WORLD)
	############# create references for Kmeans
	ref_list = []
	for index in xrange(2):
		partids = os.path.join(workdir,"new_class%d.txt"%index)
		while not os.path.exists(partids):
			#print  " my_id",myid
			sleep(2)
		mpi_barrier(MPI_COMM_WORLD)
		data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nxinit"],partids,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
		vol = recons3d_4nn_ctf_MPI(myid=myid,prjlist = data,symmetry=Tracker["constants"]["sym"],finfo=None)
		vol = filt_tanl(vol,Tracker["constants"]["low_pass_filter"],.1)
		ref_list.append(vol)
	mpi_barrier(MPI_COMM_WORLD)
	#### Kmeans
	
def count_chunk_members(chunk_dict,one_class):
	if len(one_class)==0:
		return 0,0,0
	else:
		N_chunk0 = 0.0
		N_chunk1 = 0.0
		for a in one_class:
			if chunk_dict[a]==0:
				N_chunk0 +=1.
			else:
				N_chunk1 +=1
		rate0 = N_chunk0/len(one_class)
		rate1 = N_chunk1/len(one_class) 
		return rate0,rate1,len(one_class)

def get_sorting_params_refine(Tracker,data):
	from mpi import mpi_barrier, MPI_COMM_WORLD
	from utilities import read_text_row,wrap_mpi_bcast,even_angles
	from applications import MPI_start_end
	myid      = Tracker["constants"]["myid"]
	main_node = Tracker["constants"]["main_node"]
	nproc     = Tracker["constants"]["nproc"]
	ndata     = Tracker["total_stack"]
	mpi_comm  = MPI_COMM_WORLD
	if myid == main_node:
		total_attr_value_list = []
		for n in xrange(ndata):
			total_attr_value_list.append([])
	else:
		total_attr_value_list = 0
	for inode in xrange(nproc):
		attr_value_list =get_sorting_attr_stack(data)
		attr_value_list =wrap_mpi_bcast(attr_value_list,inode)
		if myid ==main_node:
			image_start,image_end=MPI_start_end(ndata,nproc,inode)
			total_attr_value_list=fill_in_mpi_list(total_attr_value_list,attr_value_list,image_start,image_end)		
		mpi_barrier(MPI_COMM_WORLD)
	total_attr_value_list = wrap_mpi_bcast(total_attr_value_list,main_node)
	return total_attr_value_list
	
def get_sorting_attr_stack(data_stack):
	from utilities import get_params_proj
	attr_value_list = []
	for idat in xrange(len(data_stack)):
		group = data_stack[idat].get_attr("group")
		phi,theta,psi,s2x,s2y=get_params_proj(data_stack[idat],xform = "xform.projection")
		attr_value_list.append([group, phi, theta, psi, s2x, s2y])
	return attr_value_list
	
def parsing_sorting_params(sorting_params_list):
	group_list        = []
	ali3d_params_list = []
	for element in sorting_params_list:
		group_list.append(element[0]) 
		ali3d_params_list.append(element[1:])
	return group_list, ali3d_params_list
	
def adjust_fsc_down(fsc,n1,n2):
	# fsc curve:  frequencies   cc values  number of the sampling points
	# n1 total data n2 subset
	from utilities import read_text_file
	import types
	if type(fsc) == types.StringType:fsc=read_text_file(fsc,-1)
	N_bins =  len(fsc[0])
	adjusted_fsc = N_bins*[None]
	for index_of_cc in xrange(N_bins):
		adjusted_fsc[index_of_cc] = (float(n2)/float(n1))*fsc[1][index_of_cc]/(1.-(1.-float(n2)/float(n1))*fsc[1][index_of_cc])
	calibrated_fsc=[fsc[0], adjusted_fsc, fsc[2]]
	return calibrated_fsc
	
def set_filter_parameters_from_adjusted_fsc(n1,n2,Tracker):
	## use the smallest group 
	fsc_cutoff   = 1.0/3.0
	adjusted_fsc = adjust_fsc_down(Tracker["global_fsc"],n1,n2)
	currentres   = -1.0
	ns           = len(adjusted_fsc)
	for i in xrange(1,ns-1):
		if adjusted_fsc[1][i] < fsc_cutoff:
			currentres = adjusted_fsc[0][i-1]
			break
	lowpass, falloff    = fit_tanh1(adjusted_fsc, 0.01)
	lowpass             = round(lowpass,4)
	if Tracker["constants"]["myid"] ==Tracker["constants"]["main_node"]:
		Tracker["constants"]["log_main"].add("the determined low pass filter is %5.3f"%lowpass) 	
	falloff             = round(falloff,4)
	currentres          = round(currentres,2)
	Tracker["lowpass"] = lowpass
	Tracker["falloff"]  =min(Tracker["falloff"],falloff)
	
def search_lowpass(fsc):
	fcutoff =.5
	for i in xrange(len(fsc[1])):
		if fsc[0][i]<.5:
			break
	if i<len(fsc[1])-1:
		fcutoff=fsc[0][i-1]
	else:
		fcutoff=.5
	fcutoff=min(.45,fcutoff)
	return fcutoff
	
def main():
	from time import sleep
	from logger import Logger, BaseLogger_Files
        arglist = []
        i = 0
        while( i < len(sys.argv) ):
            if sys.argv[i]=='-p4pg':
                i = i+2
            elif sys.argv[i]=='-p4wd':
                i = i+2
            else:
                arglist.append( sys.argv[i] )
                i = i+1
	progname = os.path.basename(arglist[0])
	usage = progname + " stack  outdir  <mask> --focus=3Dmask --radius=outer_radius --delta=angular_step" +\
	"--an=angular_neighborhood --maxit=max_iter  --CTF --sym=c1 --function=user_function --independent=indenpendent_runs  --number_of_images_per_group=number_of_images_per_group  --low_pass_frequency=.25  --seed=random_seed"
	parser = OptionParser(usage,version=SPARXVERSION)
	parser.add_option("--focus",         type="string",       default=None,             help="3D mask for focused clustering ")
	parser.add_option("--ir",            type= "int",         default= 1, 	            help="inner radius for rotational correlation > 0 (set to 1)")
	parser.add_option("--radius",        type= "int",         default=-1,	            help="outer radius for rotational correlation <nx-1 (set to the radius of the particle)")
	parser.add_option("--maxit",	     type= "int",         default=50, 	            help="maximum number of iteration")
	parser.add_option("--rs",            type= "int",         default=1,	            help="step between rings in rotational correlation >0 (set to 1)" ) 
	parser.add_option("--xr",            type="string",       default='1',              help="range for translation search in x direction, search is +/-xr ")
	parser.add_option("--yr",            type="string",       default='-1',	            help="range for translation search in y direction, search is +/-yr (default = same as xr)")
	parser.add_option("--ts",            type="string",       default='0.25',           help="step size of the translation search in both directions direction, search is -xr, -xr+ts, 0, xr-ts, xr ")
	parser.add_option("--delta",         type="string",       default='2',              help="angular step of reference projections")
	parser.add_option("--an",            type="string",       default='-1',	            help="angular neighborhood for local searches")
	parser.add_option("--center",        type="int",          default=0,	            help="0 - if you do not want the volume to be centered, 1 - center the volume using cog (default=0)")
	parser.add_option("--nassign",       type="int",          default=1, 	            help="number of reassignment iterations performed for each angular step (set to 3) ")
	parser.add_option("--nrefine",         type="int",          default=0, 	            help="number of alignment iterations performed for each angular step (set to 1) ")
	parser.add_option("--CTF",             action="store_true", default=False,             help="Consider CTF correction during the alignment ")
	parser.add_option("--stoprnct",        type="float",        default=3.0,               help="Minimum percentage of assignment change to stop the program")
	parser.add_option("--sym",             type="string",       default='c1',              help="symmetry of the structure ")
	parser.add_option("--function",        type="string",       default='do_volume_mrk02', help="name of the reference preparation function")
	parser.add_option("--independent",     type="int",          default= 3,                help="number of independent run")
	parser.add_option("--number_of_images_per_group",           type='int',                default=1000, help="number of groups")
	parser.add_option("--low_pass_filter",  type="float",       default=-1.0,              help="absolute frequency of low-pass filter for 3d sorting on the original image size" )
	parser.add_option("--nxinit",           type="int",         default=64,                help="initial image size for sorting" )
	parser.add_option("--unaccounted",   action="store_true",   default=False,             help="reconstruct the unaccounted images")
	parser.add_option("--seed", type="int", default=-1,                             help="random seed for create initial random assignment for EQ Kmeans")
	parser.add_option("--smallest_group", type="int",    default=500,               help="minimum members for identified group" )
	parser.add_option("--previous_run1",  type="string",default='',                 help="two previous runs" )
	parser.add_option("--previous_run2",  type="string",default='',                 help="two previous runs" )
	parser.add_option("--group_size_for_unaccounted",  type="int",default=500,      help="size for unaccounted particles" )
	parser.add_option("--chunkdir", type="string",               default='',        help="chunkdir for computing margin of error")
	parser.add_option("--sausage",   action="store_true",        default=False,     help="way of filter volume")
	parser.add_option("--PWadjustment", type="string",           default=None,      help="1-D power spectrum of PDB file used for EM volume power spectrum correction")
	parser.add_option("--upscale", type="float",                 default=0.5,       help=" scaling parameter to adjust the power spectrum of EM volumes")
	parser.add_option("--wn", type="int",                        default=0,         help="optimal window size for data processing")
	(options, args) = parser.parse_args(arglist[1:])
	if len(args) < 1  or len(args) > 4:
    		print "usage: " + usage
    		print "Please run '" + progname + " -h' for detailed options"
	else:

		if len(args)>2:
			mask_file = args[2]
		else:
			mask_file = None

		orgstack                        =args[0]
		masterdir                       =args[1]
		global_def.BATCH = True
		#---initialize MPI related variables
		from mpi import mpi_init, mpi_comm_size, MPI_COMM_WORLD, mpi_comm_rank,mpi_barrier,mpi_bcast, mpi_bcast, MPI_INT
		sys.argv  = mpi_init(len(sys.argv),sys.argv)
		nproc     = mpi_comm_size(MPI_COMM_WORLD)
		myid      = mpi_comm_rank(MPI_COMM_WORLD)
		mpi_comm  = MPI_COMM_WORLD
		main_node = 0
		# import some utilities
		from utilities import get_im,bcast_number_to_all,cmdexecute,write_text_file,read_text_file,wrap_mpi_bcast
		from applications import recons3d_n_MPI, mref_ali3d_MPI, Kmref_ali3d_MPI
		from statistics import k_means_match_clusters_asg_new,k_means_stab_bbenum
		from reconstruction import rec3D_MPI_noCTF,rec3D_two_chunks_MPI
		from applications import mref_ali3d_EQ_Kmeans, ali3d_mref_Kmeans_MPI  
		# Create the main log file
		from logger import Logger,BaseLogger_Files
		if myid ==main_node:
			log_main=Logger(BaseLogger_Files())
			log_main.prefix=masterdir+"/"
		else:
			log_main = None
		#--- fill input parameters into dictionary named after Constants
		Constants		                         ={}
		Constants["stack"]                       =args[0]
		Constants["masterdir"]                   =masterdir
		Constants["mask3D"]                      =mask_file
		Constants["focus3Dmask"]                 =options.focus
		Constants["indep_runs"]                  =options.independent
		Constants["stoprnct"]                    =options.stoprnct
		Constants["number_of_images_per_group"]  =options.number_of_images_per_group
		Constants["CTF"]                 =options.CTF
		Constants["maxit"]               =options.maxit
		Constants["ir"]                  =options.ir 
		Constants["radius"]              =options.radius 
		Constants["nassign"]             =options.nassign
		Constants["rs"]                  =options.rs 
		Constants["xr"]                  =options.xr
		Constants["yr"]                  =options.yr
		Constants["ts"]                  =options.ts
		Constants["delta"]               =options.delta
		Constants["an"]                  =options.an
		Constants["sym"]                 =options.sym
		Constants["center"]              =options.center
		Constants["nrefine"]             =options.nrefine
		Constants["user_func"]           =options.function
		Constants["low_pass_filter"]     =options.low_pass_filter # enforced low_pass_filter
		Constants["main_log_prefix"]     =args[1]
		#Constants["importali3d"]        =options.importali3d
		Constants["myid"]	             =myid
		Constants["main_node"]           =main_node
		Constants["nproc"]               =nproc
		Constants["log_main"]            =log_main
		Constants["nxinit"]              =options.nxinit
		Constants["unaccounted"]         =options.unaccounted
		Constants["seed"]                =options.seed
		Constants["smallest_group"]      =options.smallest_group
		Constants["previous_runs"]       =options.previous_run1+" "+options.previous_run2
		Constants["sausage"]             =options.sausage
		Constants["chunkdir"]            =options.chunkdir 
		Constants["PWadjustment"]        =options.PWadjustment
		Constants["upscale"]             =options.upscale
		Constants["wn"]                  =options.wn 
		#Constants["frequency_stop_search"] = options.frequency_stop_search
		#Constants["scale_of_number"]    = options.scale_of_number
		# -------------------------------------------------------------
		#
		# Create and initialize Tracker dictionary with input options
		Tracker                   = {}
		Tracker["constants"]      =	Constants
		Tracker["maxit"]          = Tracker["constants"]["maxit"]
		Tracker["radius"]         = Tracker["constants"]["radius"]
		#Tracker["xr"]            = ""
		#Tracker["yr"]            = "-1"  # Do not change!
		#Tracker["ts"]            = 1
		#Tracker["an"]            = "-1"
		#Tracker["delta"]         = "2.0"
		#Tracker["zoom"]          = True
		#Tracker["nsoft"]         = 0
		#Tracker["local"]         = False
		Tracker["PWadjustment"]   = Tracker["constants"]["PWadjustment"]
		Tracker["upscale"]        = Tracker["constants"]["upscale"]
		Tracker["applyctf"]       = False  #  Should the data be premultiplied by the CTF.  Set to False for local continuous.
		#Tracker["refvol"]        = None
		Tracker["nxinit"]         = Tracker["constants"]["nxinit"]
		#Tracker["nxstep"]        = 32
		Tracker["icurrentres"]    = -1
		#Tracker["ireachedres"]   = -1
		Tracker["lowpass"]        = Tracker["constants"]["low_pass_filter"]
		Tracker["falloff"]        = 0.1
		#Tracker["inires"]        = options.inires  # Now in A, convert to absolute before using
		Tracker["fuse_freq"]      = 50  # Now in A, convert to absolute before using
		#Tracker["delpreviousmax"]= False
		#Tracker["anger"]         = -1.0
		#Tracker["shifter"]       = -1.0
		#Tracker["saturatecrit"]  = 0.95
		#Tracker["pixercutoff"]   = 2.0
		#Tracker["directory"]     = ""
		#Tracker["previousoutputdir"] = ""
		#Tracker["eliminated-outliers"] = False
		#Tracker["mainiteration"]       = 0
		#Tracker["movedback"]           = False
		#Tracker["state"]               = Tracker["constants"]["states"][0] 
		#Tracker["global_resolution"]   = 0.0
		Tracker["orgstack"]             = orgstack
		#--------------------------------------------------------------------
		#
		# Get the pixel size; if none, set to 1.0, and the original image size
		from utilities import get_shrink_data_huang
		from time import sleep
		import user_functions
		user_func = user_functions.factory[Tracker["constants"]["user_func"]]
		if(myid == main_node):
			line = strftime("%Y-%m-%d_%H:%M:%S", localtime()) + " =>"
			print(line+"Initialization of 3-D sorting")
			a = get_im(orgstack)
			nnxo = a.get_xsize()
			if( Tracker["nxinit"] > nnxo ):
				ERROR("Image size less than minimum permitted $d"%Tracker["nxinit"],"sxsort3d.py",1)
				nnxo = -1
			else:
				if Tracker["constants"]["CTF"]:
					i = a.get_attr('ctf')
					pixel_size = i.apix
					fq = pixel_size/Tracker["fuse_freq"]
				else:
					pixel_size = 1.0
					#  No pixel size, fusing computed as 5 Fourier pixels
					fq = 5.0/nnxo
					del a
		else:
			nnxo = 0
			fq   = 0.0
			pixel_size = 1.0
		nnxo = bcast_number_to_all(nnxo, source_node = main_node)
		if( nnxo < 0 ):
			mpi_finalize()
			exit()
		pixel_size                           = bcast_number_to_all(pixel_size, source_node = main_node)
		fq                                   = bcast_number_to_all(fq, source_node = main_node)
		if Tracker["constants"]["wn"]==0:
			Tracker["constants"]["nnxo"] = nnxo
		else:
			Tracker["constants"]["nnxo"] = Tracker["constants"]["wn"]
			nnxo= Tracker["constants"]["wn"]
		Tracker["constants"]["pixel_size"]   = pixel_size
		Tracker["fuse_freq"]                 = fq
		del fq, nnxo, pixel_size
		if(Tracker["constants"]["radius"]  < 1):
			Tracker["constants"]["radius"]  = Tracker["constants"]["nnxo"]//2-2
		elif((2*Tracker["constants"]["radius"] +2) > Tracker["constants"]["nnxo"]):
			ERROR("Particle radius set too large!","sxsort3d.py",1,myid)
####-----------------------------------------------------------------------------------------
		# create the master directory
		if myid == main_node:
			if masterdir =="":
				timestring = strftime("_%d_%b_%Y_%H_%M_%S", localtime())
				masterdir ="master_sort3d"+timestring
				li =len(masterdir)
			else:
				li = 0
			cmd="{} {}".format("mkdir", masterdir)
			os.system(cmd)			
		else:
			li=0
		li = mpi_bcast(li,1,MPI_INT,main_node,MPI_COMM_WORLD)[0]
		if li>0:
			masterdir = mpi_bcast(masterdir,li,MPI_CHAR,main_node,MPI_COMM_WORLD)
			masterdir = string.join(masterdir,"")
		####--- masterdir done!
		if myid ==main_node:
			print_dict(Tracker["constants"],"Permanent settings of 3-D sorting program")
		from time import sleep
		while not os.path.exists(masterdir):  # Be sure each proc is able to access the created dir
				print  "Node ",myid,"  waiting..."
				sleep(5)
		mpi_barrier(MPI_COMM_WORLD)
		######### create a vstack from input stack to the local stack in masterdir
		# stack name set to default
		Tracker["constants"]["stack"]     = "bdb:"+masterdir+"/rdata"
		Tracker["constants"]["ali3d"]     = os.path.join(masterdir, "ali3d_init.txt")
		Tracker["constants"]["partstack"] = Tracker["constants"]["ali3d"]
		######
		"""
	   	if myid == main_node:
			if(orgstack[:4] == "bdb:"):     cmd = "{} {} {}".format("e2bdb.py", orgstack,"--makevstack="+Tracker["constants"]["stack"])
			else:  cmd = "{} {} {}".format("sxcpy.py", orgstack, Tracker["constants"]["stack"])
			cmdexecute(cmd)
			cmd = "{} {}".format("sxheader.py  --consecutive  --params=originalid", Tracker["constants"]["stack"])
			cmdexecute(cmd)
			cmd = "{} {} {} {} ".format("sxheader.py", Tracker["constants"]["stack"],"--params=xform.projection","--export="+Tracker["constants"]["ali3d"])
			cmdexecute(cmd)
			keepchecking = False
			total_stack = EMUtil.get_image_count(Tracker["constants"]["stack"])
		else:
			total_stack =0
		"""
		########## ---------------new way of read data in --------------------##########
		if myid==main_node:
	   		total_stack = EMUtil.get_image_count(orgstack)
	   	else:
	   		total_stack =0
	   	total_stack = bcast_number_to_all(total_stack, source_node = main_node)
		if myid==main_node:
	   		from EMAN2db import db_open_dict	
	   		OB = db_open_dict(orgstack)
	   		DB = db_open_dict(Tracker["constants"]["stack"]) 
			for i in xrange(total_stack):
				DB[i] = OB[i]
			OB.close()
			DB.close()
	   	mpi_barrier(MPI_COMM_WORLD)
	   	if myid==main_node:
			params= []
			for i in xrange(total_stack):
				e=get_im(orgstack,i)
				phi,theta,psi,s2x,s2y = get_params_proj(e)
				params.append([phi,theta,psi,s2x,s2y])
			write_text_row(params,Tracker["constants"]["ali3d"])
		mpi_barrier(MPI_COMM_WORLD)
		#Tracker["total_stack"]             = total_stack
		Tracker["constants"]["total_stack"] = total_stack
		Tracker["shrinkage"]                = float(Tracker["nxinit"])/Tracker["constants"]["nnxo"]
		#####------------------------------------------------------------------------------
		if Tracker["constants"]["mask3D"]:
			Tracker["mask3D"]=os.path.join(masterdir,"smask.hdf")
		else:Tracker["mask3D"] = None
		if Tracker["constants"]["focus3Dmask"]:
			Tracker["focus3D"]=os.path.join(masterdir,"sfocus.hdf")
		else: Tracker["focus3D"] = None
		if myid ==main_node:
			if Tracker["constants"]["mask3D"]:
				mask_3D = get_shrink_3dmask(Tracker["nxinit"],Tracker["constants"]["mask3D"])
				mask_3D.write_image(Tracker["mask3D"])
			if Tracker["constants"]["focus3Dmask"]:
				mask_3D = get_shrink_3dmask(Tracker["nxinit"],Tracker["constants"]["focus3Dmask"])
				st = Util.infomask(mask_3D, None, True)
				if( st[0] == 0.0 ):  ERROR("sxrsort3d","incorrect focused mask, after binarize all values zero",1)
				mask_3D.write_image(Tracker["focus3D"])
				del mask_3D
		if Tracker["constants"]["PWadjustment"]:
			PW_dict={}
			nxinit_pwsp=sample_down_1D_curve(Tracker["constants"]["nxinit"],Tracker["constants"]["nnxo"],Tracker["constants"]["PWadjustment"])
			Tracker["nxinit_PW"] = os.path.join(masterdir,"spwp.txt")
			if myid ==main_node:
				write_text_file(nxinit_pwsp,Tracker["nxinit_PW"])
			PW_dict[Tracker["constants"]["nnxo"]]   =Tracker["constants"]["PWadjustment"]
			PW_dict[Tracker["constants"]["nxinit"]] =Tracker["nxinit_PW"]
			Tracker["PW_dict"] = PW_dict 
		###----------------------------------------------------------------------------------		
		####---------------------------Extract the previous results#####################################################
		from random import shuffle
		if myid ==main_node:
			log_main.add("Extract stable groups from previous runs")
			stable_member_list           = get_stable_members_from_two_runs(Tracker["constants"]["previous_runs"],Tracker["constants"]["total_stack"],log_main)
			leftover_list, new_stable_P1 = get_leftover_from_stable(stable_member_list,Tracker["constants"]["total_stack"] ,Tracker["constants"]["smallest_group"])
			total_stack                  = len(leftover_list)
			leftover_list.sort()
			log_main.add("new stable is %d"%len(new_stable_P1))
		else:
			total_stack   = 0
			leftover_list = 0
			stable_member_list =0
		stable_member_list               = wrap_mpi_bcast(stable_member_list, main_node)
		total_stack                      = bcast_number_to_all(total_stack, source_node = main_node)
		leftover_list                    = wrap_mpi_bcast(leftover_list, main_node)
		Tracker["total_stack"]           = total_stack
		Tracker["this_unaccounted_list"] = leftover_list
		#################################### Estimate resolution----------------------############# 
		#### make chunkdir dictionary for computing margin of error
		chunk_dict = {}
		chunk_list = []
		if Tracker["constants"]["chunkdir"] !="":
			if myid == main_node:
				chunk_one = read_text_file(os.path.join(Tracker["constants"]["chunkdir"],"chunk0.txt"))
				chunk_two = read_text_file(os.path.join(Tracker["constants"]["chunkdir"],"chunk1.txt"))
			else:
				chunk_one = 0
				chunk_two = 0
			chunk_one = wrap_mpi_bcast(chunk_one, main_node)
			chunk_two = wrap_mpi_bcast(chunk_two, main_node)
		else:
			if myid ==main_node:
				ll=range(total_stack)
				shuffle(ll)
				chunk_one =ll[0:total_stack//2]
				chunk_two =ll[total_stack//2:]
				del ll
				chunk_one.sort()
				chunk_two.sort()
			else:
				chunk_one = 0
				chunk_two = 0
			chunk_one = wrap_mpi_bcast(chunk_one, main_node)
			chunk_two = wrap_mpi_bcast(chunk_two, main_node)
		###### Fill chunk ID into headers
		mpi_barrier(MPI_COMM_WORLD)
		#------------------------------------------------------------------------------
		for element in chunk_one: chunk_dict[element] = 0
		for element in chunk_two: chunk_dict[element] = 1
		chunk_list =[chunk_one, chunk_two]
		Tracker["chunk_dict"] =chunk_dict
		Tracker["P_chunk0"]   =len(chunk_one)/float(Tracker["constants"]["total_stack"])
		Tracker["P_chunk1"]   =len(chunk_two)/float(Tracker["constants"]["total_stack"])
		### create two volumes to estimate resolution
		#Tracker["this_data_list"] = chunk_one
		if myid == main_node:
			for index in xrange(2):
				partids = os.path.join(masterdir,"chunk%d.txt"%index)
				write_text_file(chunk_list[index],partids)
		mpi_barrier(MPI_COMM_WORLD)
		vols = []
		for index in xrange(2):
			partids= os.path.join(masterdir,"chunk%d.txt"%index)
			while not os.path.exists(partids):
				#print  " my_id",myid
				sleep(3)
			mpi_barrier(MPI_COMM_WORLD)
			data1,old_shifts1 = get_shrink_data_huang(Tracker,Tracker["constants"]["nxinit"],partids, Tracker["constants"]["partstack"], myid, main_node, nproc, preshift = True)
			vol1 = recons3d_4nn_ctf_MPI(myid=myid,prjlist=data1,symmetry=Tracker["constants"]["sym"],finfo=None)
			if myid ==main_node:
				vol1_file_name = os.path.join(masterdir, "vol%d.hdf"%index)
				vol1.write_image(vol1_file_name)
			vols.append(vol1)
			mpi_barrier(MPI_COMM_WORLD)
		if myid ==main_node:
			low_pass, falloff,currentres =get_resolution_mrk01(vols,Tracker["constants"]["radius"]*Tracker["shrinkage"],\
			Tracker["constants"]["nxinit"],masterdir,Tracker["mask3D"])
			if low_pass   > Tracker["constants"]["low_pass_filter"]:
				low_pass  = Tracker["constants"]["low_pass_filter"]
		else:
			low_pass    =0.0
			falloff     =0.0
			currentres  =0.0
		currentres                    =bcast_number_to_all(currentres,source_node = main_node)
		low_pass                      =bcast_number_to_all(low_pass,source_node   = main_node)
		falloff                       =bcast_number_to_all(falloff,source_node    = main_node)
		Tracker["currentres"]         =currentres
		####################################################################
		Tracker["falloff"] = falloff
		if Tracker["constants"]["low_pass_filter"] ==-1.0:
			Tracker["low_pass_filter"]=low_pass*Tracker["shrinkage"]
		else:
			Tracker["low_pass_filter"] = Tracker["constants"]["low_pass_filter"]/Tracker["shrinkage"]
		Tracker["lowpass"]             = Tracker["low_pass_filter"]
		Tracker["falloff"]             = 0.1
		Tracker["global_fsc"]          = os.path.join(masterdir,"fsc.txt")
		##################################################################
		if myid ==main_node:
			log_main.add("The command-line inputs are\:")
			log_main.add("**********************************************************")
		for a in sys.argv:
			if myid ==main_node:
				log_main.add(a)
			else:
				continue
		if myid ==main_node:
			log_main.add("**********************************************************")
		from filter import filt_tanl
		##################### START 3-D sorting ##########################
		if myid ==main_node:
			log_main.add("----------3-D sorting  program------- ")
			log_main.add("current resolution %6.3f for images of original size in terms of absolute frequency"%Tracker["currentres"])
			log_main.add("equivalent to %f Angstrom resolution"%(Tracker["constants"]["pixel_size"]/Tracker["currentres"]/Tracker["shrinkage"]))
			#log_main.add("the user provided enforced low_pass_filter is %f"%Tracker["constants"]["low_pass_filter"])
			#log_main.add("equivalent to %f Angstrom resolution"%(Tracker["constants"]["pixel_size"]/Tracker["constants"]["low_pass_filter"]))
			vol1_file_name =os.path.join(masterdir, "vol0.hdf")
			vol1 = get_im(vol1_file_name)
			vol1 = filt_tanl(vol1, Tracker["low_pass_filter"], 0.1)
			volf1_file_name = os.path.join(masterdir, "volf0.hdf")
			vol1.write_image(volf1_file_name)
			vol2_file_name = os.path.join(masterdir, "vol1.hdf")
			vol2 = get_im(vol2_file_name)
			volf2_file_name = os.path.join(masterdir, "volf1.hdf")
			vol2 = filt_tanl(vol2, Tracker["low_pass_filter"], 0.1)
			vol2.write_image(volf2_file_name)
		mpi_barrier(MPI_COMM_WORLD)
		from utilities import get_input_from_string
		delta       = get_input_from_string(Tracker["constants"]["delta"])
		delta       = delta[0]
		from utilities import even_angles
		n_angles = even_angles(delta, 0, 180)
		this_ali3d  = Tracker["constants"]["ali3d"]
		sampled = get_stat_proj(Tracker,delta,this_ali3d)
		if myid ==main_node:
        		nc = 0
        		for a in sampled:
                		if len(sampled[a])>0:nc +=1
			log_main.add("total sampled direction %10d  at angle step %6.3f"%(len(n_angles), delta)) 
			log_main.add("captured sampled directions %10d percentage covered by data  %6.3f"%(nc,float(nc)/len(n_angles)*100))
		mpi_barrier(MPI_COMM_WORLD)
		## ---------------------------------------------------------------------------------------------########
		## Stop program and output results when the leftover is not sufficient for a new run    		########
		## ---------------------------------------------------  ---------------------------------------  ######
		number_of_groups = get_number_of_groups(Tracker["total_stack"],Tracker["constants"]["number_of_images_per_group"])
		if number_of_groups<=1:
			if myid ==main_node:
				log_main.add("the unaccounted ones are no sufficient for a simple two-group run, output results!")
				log_main.add("the final reproducibility is  %f"%((Tracker["constants"]["total_stack"]-len(leftover_list))/float(Tracker["constants"]["total_stack"])))
				for i in xrange(len(stable_member_list)):
					write_text_file(stable_member_list[i], os.path.join(masterdir,"P2_final_class%d.txt"%i))
				mask3d= get_im(Tracker["constants"]["mask3D"])
			else:
				mask3d=model_blank(Tracker["constants"]["nnxo"],Tracker["constants"]["nnxo"],Tracker["constants"]["nnxo"])
			bcast_EMData_to_all(mask3d,myid,main_node)
			for igrp in xrange(len(stable_member_list)):
				name_of_class_file = os.path.join(masterdir, "P2_final_class%d.txt"%igrp)
				data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nnxo"],name_of_class_file,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
				if Tracker["constants"]["CTF"]: 
					volref, fscc = rec3D_two_chunks_MPI(data,1.0,Tracker["constants"]["sym"],mask3d,os.path.join(masterdir,"resolution_%02d.txt"%igrp),myid,main_node,index =-1,npad=2,finfo=None)
				else: 
					print "Missing CTF flag!"
					from mpi import mpi_finalize
					mpi_finalize()
					exit()
				mpi_barrier(MPI_COMM_WORLD)
				fscc=read_text_file(os.path.join(masterdir,"resolution_%02d.txt"%igrp),-1)
				#nx_of_image=volref.get_xsize()
				if Tracker["constants"]["PWadjustment"]:Tracker["PWadjustment"]=Tracker["PW_dict"][Tracker["constants"]["nnxo"]]
				else:Tracker["PWadjustment"]=Tracker["constants"]["PWadjustment"]	
				try: 
					lowpass = search_lowpass(fscc)
					falloff =.1
				except:
					lowpass=.4
					falloff=.1
				if myid ==main_node:
					log_main.add(" lowpass and falloff from fsc are %f %f"%(lowpass,falloff))
				lowpass=round(lowpass,4)
				falloff=round(min(0.1,falloff),4)
				Tracker["lowpass"]= lowpass
				Tracker["falloff"]= falloff
				refdata           = [None]*4
				refdata[0]        = volref
				refdata[1]        = Tracker
				refdata[2]        = Tracker["constants"]["myid"]
				refdata[3]        = Tracker["constants"]["nproc"]
				volref            = user_func(refdata)
				if myid == main_node:
					cutoff=Tracker["constants"]["pixel_size"]/lowpass
					log_main.add("%d vol low pass filer %f   %f  cut to  %f Angstrom"%(igrp,Tracker["lowpass"],Tracker["falloff"],cutoff))
					volref.write_image(os.path.join(masterdir,"volf_final%d.hdf"%igrp))
			mpi_barrier(MPI_COMM_WORLD)			
			from mpi import mpi_finalize
			mpi_finalize()
			exit()
		#########################################################################################################################
		#if Tracker["constants"]["number_of_images_per_group"] ==-1: # Estimate number of images per group from delta, and scale up 
		#    or down by scale_of_number
		#	number_of_images_per_group = int(Tracker["constants"]["scale_of_number"]*len(n_angles))
		#
		#########################################################################################################################P2
		P2_partitions        = []
		number_of_P2_runs    = 2  # Notice P2 start from two P1 runs
		### input list_to_be_processed
		import copy
		mpi_barrier(MPI_COMM_WORLD)
		for iter_P2_run in xrange(number_of_P2_runs):
			list_to_be_processed = copy.deepcopy(leftover_list)
			if myid == main_node :    new_stable1 =  copy.deepcopy(new_stable_P1)
			total_stack   = len(list_to_be_processed) # This is the input from two P1 runs
			number_of_images_per_group = Tracker["constants"]["number_of_images_per_group"]
			P2_run_dir = os.path.join(masterdir, "P2_run%d"%iter_P2_run)
			if myid == main_node:
				cmd="{} {}".format("mkdir",P2_run_dir)
				os.system(cmd)
				log_main.add("----------------P2 independent run %d--------------"%iter_P2_run)
				log_main.add("user provided number_of_images_per_group %d"%number_of_images_per_group)
			mpi_barrier(MPI_COMM_WORLD)
			Tracker["number_of_images_per_group"] = number_of_images_per_group
			number_of_groups                      = get_number_of_groups(total_stack,number_of_images_per_group)
			generation                            = 0
			if myid ==main_node:
				log_main.add("number of groups is %d"%number_of_groups)
				log_main.add("total stack %d"%total_stack)
			while number_of_groups>=2:
				partition_dict ={}
				full_dict      ={}
				workdir             = os.path.join(P2_run_dir,"generation%03d"%generation)
				Tracker["this_dir"] = workdir
				if myid ==main_node:
					cmd="{} {}".format("mkdir",workdir)
					os.system(cmd)
					log_main.add("---- generation         %5d"%generation)
					log_main.add("number of images per group is set as %d"%number_of_images_per_group)
					log_main.add("the initial number of groups is  %10d "%number_of_groups)
					log_main.add(" the number to be processed in this generation is %d"%len(list_to_be_processed))
					#core=read_text_row(Tracker["constants"]["ali3d"],-1)
					#write_text_row(core, os.path.join(workdir,"node%d.txt"%myid))
				mpi_barrier(MPI_COMM_WORLD)
				Tracker["number_of_groups"]       = number_of_groups
				Tracker["this_data_list"]         = list_to_be_processed # leftover of P1 runs
				Tracker["total_stack"]            = len(list_to_be_processed)
				create_random_list(Tracker)
				###------ For super computer    ##############
				update_full_dict(list_to_be_processed,Tracker)
				###--------------------------------------------
				##### ----------------independent runs for EQ-Kmeans  ------------------------------------
				for indep_run in xrange(Tracker["constants"]["indep_runs"]):
					Tracker["this_particle_list"] = Tracker["this_indep_list"][indep_run]
					ref_vol = recons_mref(Tracker)
					if myid ==main_node:
						log_main.add("independent run  %10d"%indep_run)
					mpi_barrier(MPI_COMM_WORLD)
					this_particle_text_file = os.path.join(workdir,"independent_list_%03d.txt"%indep_run) # for get_shrink_data
					if myid ==main_node:
						write_text_file(list_to_be_processed,this_particle_text_file)
					from time import sleep
					while not os.path.exists(this_particle_text_file):
						print  "Node ",myid,"  waiting..."
						sleep(5)
					mpi_barrier(MPI_COMM_WORLD)
					outdir = os.path.join(workdir, "EQ_Kmeans%03d"%indep_run)
					#ref_vol= apply_low_pass_filter(ref_vol,Tracker)
					mref_ali3d_EQ_Kmeans(ref_vol, outdir, this_particle_text_file, Tracker)
					partition_dict[indep_run] = Tracker["this_partition"]
					del ref_vol
					Tracker["partition_dict"]    = partition_dict
					Tracker["this_total_stack"]  = Tracker["total_stack"]
				do_two_way_comparison(Tracker)
				##############################
				if myid ==main_node:log_main.add("Now calculate stable volumes")
				ref_vol_list = []
				if myid ==main_node:
					for igrp in xrange(len(Tracker["two_way_stable_member"])):
						Tracker["this_data_list"]      = Tracker["two_way_stable_member"][igrp]
						Tracker["this_data_list_file"] = os.path.join(workdir,"stable_class%d.txt"%igrp)
						write_text_file(Tracker["this_data_list"],Tracker["this_data_list_file"])
				mpi_barrier(MPI_COMM_WORLD)
				number_of_ref_class = []
				for igrp in xrange(len(Tracker["two_way_stable_member"])):
					Tracker["this_data_list_file"] = os.path.join(workdir,"stable_class%d.txt"%igrp)
					Tracker["this_data_list"]      = Tracker["two_way_stable_member"][igrp]
					while not os.path.exists(Tracker["this_data_list_file"]):
						#print  " my_id",myid
						sleep(2)
					mpi_barrier(MPI_COMM_WORLD)
					data,old_shifts = get_shrink_data_huang(Tracker,Tracker["nxinit"],Tracker["this_data_list_file"],Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
					volref = recons3d_4nn_ctf_MPI(myid=myid,prjlist=data,symmetry=Tracker["constants"]["sym"],finfo=None)
					ref_vol_list.append(volref)
					number_of_ref_class.append(len(Tracker["this_data_list"]))
				if myid ==main_node:
					log_main.add("group  %d  members %d "%(igrp,len(Tracker["this_data_list"])))	
				#ref_vol_list=apply_low_pass_filter(ref_vol_list,Tracker)
				if myid ==main_node:
					for iref in xrange(len(ref_vol_list)):
						ref_vol_list[iref].write_image(os.path.join(workdir,"vol_stable.hdf"),iref)
				mpi_barrier(MPI_COMM_WORLD)
				################################
				Tracker["number_of_ref_class"] =number_of_ref_class
				Tracker["this_data_list"] =Tracker["this_accounted_list"]
				outdir                    = os.path.join(workdir,"Kmref")  
				empty_groups,res_classes,final_list = ali3d_mref_Kmeans_MPI(ref_vol_list,outdir,Tracker["this_accounted_text"],Tracker)
				complementary = get_complementary_elements(list_to_be_processed,final_list)
				Tracker["this_unaccounted_list"] = complementary
				if myid ==main_node:
					log_main.add("the number of particles not processed is %d"%len(complementary))
				update_full_dict(complementary,Tracker)
				if myid ==main_node: write_text_file(Tracker["this_unaccounted_list"],Tracker["this_unaccounted_text"])
				number_of_groups = len(res_classes)
				### Update data
				mpi_barrier(MPI_COMM_WORLD)
				if myid == main_node:
					number_of_ref_class=[]
					log_main.add(" Compute volumes of original size")
					for igrp in xrange(number_of_groups):
						class_file = os.path.join(outdir,"Class%d.txt"%igrp)
						if os.path.exists(class_file):
							this_class=read_text_file(class_file)
							new_stable1.append(this_class)
							log_main.add(" read Class file %d"%igrp)
							number_of_ref_class.append(len(new_stable1))
				else:
					number_of_ref_class=0
				number_of_ref_class = wrap_mpi_bcast(number_of_ref_class,main_node)
				################################
				mpi_barrier(MPI_COMM_WORLD)
				if myid ==main_node:
					vol_list = []
				for igrp in xrange(number_of_groups):
					class_file = os.path.join(outdir,"Class%d.txt"%igrp)
					if os.path.exists(class_file):
						if myid ==main_node:log_main.add("start vol   %d"%igrp)
					while not os.path.exists(class_file):
						#print  " my_id",myid
						sleep(2)
					mpi_barrier(MPI_COMM_WORLD)
					data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nnxo"],class_file,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
					volref          = recons3d_4nn_ctf_MPI(myid=myid, prjlist = data, symmetry=Tracker["constants"]["sym"],finfo=None)
					if myid ==main_node: 
						vol_list.append(volref)
						log_main.add(" vol   %d is done"%igrp)
				Tracker["number_of_ref_class"]=number_of_ref_class
				mpi_barrier(MPI_COMM_WORLD)
				generation +=1
				#################################
				if myid ==main_node:
					for ivol in xrange(len(vol_list)):
						vol_list[ivol].write_image(os.path.join(workdir, "vol_of_Classes.hdf"),ivol)
					filt_tanl(vol_list[ivol],Tracker["constants"]["low_pass_filter"],.1).write_image(os.path.join(workdir, "volf_of_Classes.hdf"),ivol)
					log_main.add("number of unaccounted particles  %10d"%len(Tracker["this_unaccounted_list"]))
					log_main.add("number of accounted particles  %10d"%len(Tracker["this_accounted_list"]))
					del vol_list
				Tracker["this_data_list"]        = complementary
				Tracker["total_stack"]           = len(complementary)
				Tracker["this_total_stack"]      = Tracker["total_stack"]
				#update_full_dict(complementary)
				#number_of_groups = int(float(len(Tracker["this_unaccounted_list"]))/number_of_images_per_group)
				del list_to_be_processed
				list_to_be_processed = copy.deepcopy(complementary)
				number_of_groups                 = get_number_of_groups(len(list_to_be_processed),number_of_images_per_group)
				Tracker["number_of_groups"]      = number_of_groups
				mpi_barrier(MPI_COMM_WORLD)
#############################################################################################################################
			### reconstruct the unaccounted is only done once
			if Tracker["constants"]["unaccounted"] and len(Tracker["this_unaccounted_list"])!=0:
				while not os.path.exists(Tracker["this_unaccounted_text"]):
					#print  " my_id",myid
					sleep(2)
				mpi_barrier(MPI_COMM_WORLD)
				data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nnxo"],Tracker["this_unaccounted_text"],Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
				volref = recons3d_4nn_ctf_MPI(myid=myid, prjlist = data, symmetry=Tracker["constants"]["sym"],finfo=None)
				volref = filt_tanl(volref, Tracker["constants"]["low_pass_filter"],.1)
				if myid ==main_node:
					volref.write_image(os.path.join(workdir, "volf_unaccounted.hdf"))
			######## Exhaustive Kmeans #############################################
			if myid ==main_node:
				if len(Tracker["this_unaccounted_list"])>=Tracker["constants"]["smallest_group"]:
					new_stable1.append(Tracker["this_unaccounted_list"])
				unaccounted      = get_complementary_elements_total(Tracker["constants"]["total_stack"], final_list)
				number_of_groups = len(new_stable1)
				log_main.add("----------------Exhaustive Kmeans------------------")
				log_main.add("number_of_groups is %d"%number_of_groups)
			else:number_of_groups=0
			if myid == main_node:
				final_list =[]
				for alist in new_stable1:
					for element in alist:final_list.append(int(element))
				unaccounted=get_complementary_elements_total(Tracker["constants"]["total_stack"],final_list)
				if len(unaccounted) >Tracker["constants"]["smallest_group"]:
					new_stable1.append(unaccounted)
					number_of_groups=len(new_stable1)
					for any in unaccounted:final_list.append(any)
				log_main.add("total number %d"%len(final_list))
			else:final_list = 0
			number_of_groups= bcast_number_to_all(number_of_groups,source_node=main_node)
			Tracker["number_of_groups"] =number_of_groups
			mpi_barrier(MPI_COMM_WORLD)
			final_list = wrap_mpi_bcast(final_list,main_node)
			workdir = os.path.join(P2_run_dir,"Exhaustive_Kmeans")
			final_list_text_file=os.path.join(workdir,"final_list.txt")
			if myid==main_node:
				os.mkdir(workdir)
				write_text_file(final_list,final_list_text_file)
			else:new_stable1 =0
			mpi_barrier(MPI_COMM_WORLD)
			## Create reference volumes
			ref_vol_list = []
			if myid == main_node:
				number_of_ref_class= []
				for igrp in xrange(number_of_groups):
					class_file = os.path.join(workdir,"final_class%d.txt"%igrp)
					write_text_file(new_stable1[igrp],class_file)
					log_main.add(" group %d   number of particles %d"%(igrp,len(new_stable1[igrp])))
					number_of_ref_class.append(len(new_stable1[igrp]))
			else:number_of_ref_class= 0
			number_of_ref_class = wrap_mpi_bcast(number_of_ref_class,main_node)
			mpi_barrier(MPI_COMM_WORLD)
			for igrp in xrange(number_of_groups):
				while not os.path.exists(Tracker["this_unaccounted_text"]):
					#print  " my_id",myid
					sleep(2)
				mpi_barrier(MPI_COMM_WORLD)
				Tracker["this_data_list_file"] = os.path.join(workdir,"final_class%d.txt"%igrp)
				data,old_shifts = get_shrink_data_huang(Tracker,Tracker["nxinit"],Tracker["this_data_list_file"],Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
				volref = recons3d_4nn_ctf_MPI(myid=myid, prjlist = data, symmetry=Tracker["constants"]["sym"], finfo=None)
				#volref = filt_tanl(volref, Tracker["low_pass_filter"],.1)
				#if myid == main_node:
				#	volref.write_image(os.path.join(masterdir,"volf_stable.hdf"),iref)
				#volref = resample(volref,Tracker["shrinkage"])
				ref_vol_list.append(volref)
			mpi_barrier(MPI_COMM_WORLD)
			Tracker["number_of_ref_class"] = number_of_ref_class
			Tracker["this_data_list"]      = final_list
			Tracker["total_stack"]         = len(final_list)
			Tracker["this_dir"]            = workdir
			Tracker["this_data_list_file"] = final_list_text_file
			KE_group =Kmeans_exhaustive_run(ref_vol_list,Tracker) # 
			P2_partitions.append(KE_group)
			if myid ==main_node:
				log_main.add(" the number of groups after exhaustive Kmeans is %d"%len(KE_group))
				for ike in xrange(len(KE_group)):log_main.add(" group   %d   number of objects %d"%(ike,len(KE_group[ike])))
				del new_stable1
			mpi_barrier(MPI_COMM_WORLD)
		if myid ==main_node:log_main.add("P2 runs are done, now start two-way comparision to exclude those that are not reproduced ")
		reproduced_groups = two_way_comparison_single(P2_partitions[0],P2_partitions[1],Tracker)# Here partition IDs are original indexes.
		###### ----------------Reconstruct reproduced groups------------------------#######
		######
		if myid ==main_node:
			for index_of_reproduced_groups in xrange(len(reproduced_groups)):
				name_of_class_file = os.path.join(masterdir, "P2_final_class%d.txt"%index_of_reproduced_groups)
				write_text_file(reproduced_groups[index_of_reproduced_groups],name_of_class_file)
			log_main.add("-------start to reconstruct reproduced volumes individully to orignal size-----------")
		mpi_barrier(MPI_COMM_WORLD)
		if Tracker["constants"]["mask3D"]: mask_3d = get_shrink_3dmask(Tracker["constants"]["nnxo"],Tracker["constants"]["mask3D"])
		else: mask_3d = None
		for igrp in xrange(len(reproduced_groups)):
			name_of_class_file = os.path.join(masterdir, "P2_final_class%d.txt"%igrp)
			#while not os.path.exists(name_of_class_file):
			#	#print  " my_id",myid
			#	sleep(2)
			#mpi_barrier(MPI_COMM_WORLD)
			data,old_shifts = get_shrink_data_huang(Tracker,Tracker["constants"]["nnxo"],name_of_class_file,Tracker["constants"]["partstack"],myid,main_node,nproc,preshift = True)
			#volref = recons3d_4nn_ctf_MPI(myid=myid, prjlist = data, symmetry=Tracker["constants"]["sym"], finfo=None)
			if Tracker["constants"]["CTF"]: 
				volref, fscc = rec3D_two_chunks_MPI(data,1.0,Tracker["constants"]["sym"],mask_3d,
			 os.path.join(masterdir,"resolution_%02d.txt"%igrp),myid,main_node,index =-1,npad =2,finfo=None)
			else: 
				print "Missing CTF flag!"
				from mpi import mpi_finalize
				mpi_finalize()
				exit()
			mpi_barrier(MPI_COMM_WORLD)
			fscc=read_text_file(os.path.join(masterdir,"resolution_%02d.txt"%igrp),-1)
			nx_of_image=volref.get_xsize()
			if Tracker["constants"]["PWadjustment"]:Tracker["PWadjustment"]=Tracker["PW_dict"][nx_of_image]
			else:Tracker["PWadjustment"]=Tracker["constants"]["PWadjustment"]	
			try:
				lowpass = search_lowpass(fscc)
				falloff =.1
			except:
				lowpass=.4
				falloff=.1
			lowpass=round(lowpass,4)
			falloff=round(min(.1,falloff),4)
			Tracker["lowpass"]=lowpass
			Tracker["falloff"]=falloff
			refdata    =[None]*4
			refdata[0] = volref
			refdata[1] = Tracker
			refdata[2] = Tracker["constants"]["myid"]
			refdata[3] = Tracker["constants"]["nproc"]
			volref = user_func(refdata)
			if myid == main_node:
				cutoff=Tracker["constants"]["pixel_size"]/lowpass
				log_main.add("%d vol low pass filer %f   %f  cut to  %f Angstrom"%(igrp,Tracker["lowpass"],Tracker["falloff"],cutoff))
				volref.write_image(os.path.join(masterdir,"volf_final%d.hdf"%igrp))
		if myid==main_node:
			log_main.add(" sxsort3d_P2 finishes. ")
		# Finish program
		mpi_barrier(MPI_COMM_WORLD)
		from mpi import mpi_finalize
		mpi_finalize()
		exit()
if __name__ == "__main__":
	main()

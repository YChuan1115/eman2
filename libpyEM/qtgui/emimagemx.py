#!/usr/bin/env python

#
# Author: Steven Ludtke (sludtke@bcm.edu)
# Copyright (c) 2000-2006 Baylor College of Medicine
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston MA 02111-1307 USA
#
#

from PyQt4 import QtCore, QtGui, QtOpenGL
from PyQt4.QtCore import Qt
from OpenGL import GL,GLU,GLUT
from OpenGL.GL import *
from OpenGL.GLU import *
from valslider import ValSlider
from math import *
from EMAN2 import *
import EMAN2
import sys
import numpy
from emimageutil import ImgHistogram,EMParentWin
from weakref import WeakKeyDictionary
from pickle import dumps,loads
from PyQt4.QtGui import QImage
from PyQt4.QtCore import QTimer

from emglobjects import EMOpenGLFlagsAndTools

class EMImageMX(QtOpenGL.QGLWidget):
	"""A QT widget for rendering EMData objects. It can display stacks of 2D images
	in 'matrix' form on the display. The middle mouse button will bring up a
	control-panel. The QT event loop must be running for this object to function
	properly.
	"""
	allim=WeakKeyDictionary()
	def __init__(self, data=None,parent=None):

		self.imagemx = None
		#self.initflag = True
		self.mmode = "drag"

		fmt=QtOpenGL.QGLFormat()
		fmt.setDoubleBuffer(True);
		QtOpenGL.QGLWidget.__init__(self,fmt, parent)
		EMImageMX.allim[self]=0
		
		
		self.imagemx = EMImageMXCore(data,self)
		
	def setData(self,data):
		self.imagemx.setData(data)
		
	def initializeGL(self):
		glClearColor(0,0,0,0)
		
	def paintGL(self):
		if not self.parentWidget() : return
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		if ( self.imagemx == None ): return
		self.imagemx.render()

	
	def resizeGL(self, width, height):
		
		GL.glViewport(0,0,width,height)
	
		GL.glMatrixMode(GL.GL_PROJECTION)
		GL.glLoadIdentity()
		GLU.gluOrtho2D(0.0,width,0.0,height)
		GL.glMatrixMode(GL.GL_MODELVIEW)
		GL.glLoadIdentity()
		
		try: self.imagemx.resizeEvent(width,height)
		except: pass
	def setmmode(self,mode):
		self.mmode = mode
		self.imagemx.mmode = mode
	
	def mousePressEvent(self, event):
		self.imagemx.mousePressEvent(event)
			
	def wheelEvent(self,event):
		self.imagemx.wheelEvent(event)
	
	def mouseMoveEvent(self,event):
		self.imagemx.mouseMoveEvent(event)

	def mouseReleaseEvent(self,event):
		self.imagemx.mouseReleaseEvent(event)
	
	def keyPressEvent(self,event):
		print "key press event"
		if self.mmode == "app":
			self.emit(QtCore.SIGNAL("keypress"),event)

	def dropEvent(self,event):
		self.imagemx.dropEvent(event)
		
	def closeEvent(self,event) :
		self.imagemx.closeEvent(event)
		
	def dragEnterEvent(self,event):
		self.imagemx.dragEnterEvent(event)

	def dropEvent(self,event):
		self.imagemx.dropEvent(event)
		
	def isVisible(self,n):
		return self.imagemx.isVisible(n)
	
	def setSelected(self,n):
		return self.imagemx.setSelected(n)
	
	def scrollTo(self,n,yonly):
		return self.imagemx.scrollTo(n,yonly)
	
class EMImageMXCore:

	allim=WeakKeyDictionary()
	def __init__(self, data=None,parent=None):
		self.parent = parent
		self.data=None
		self.datasize=(1,1)
		self.scale=1.0
		self.minden=0
		self.maxden=1.0
		self.invert=0
		self.fft=None
		self.mindeng=0
		self.maxdeng=1.0
		self.gamma=1.0
		self.origin=(0,0)
		self.nperrow=8
		self.nshow=-1
		self.mousedrag=None
		self.nimg=0
		self.changec={}
		self.mmode="drag"
		self.selected=[]
		self.targetorigin=None
		self.targetspeed=20.0
		self.mag = 1.1				# magnification factor
		self.invmag = 1.0/self.mag	# inverse magnification factor
		self.glflags = EMOpenGLFlagsAndTools() 	# supplies power of two texturing flags
		self.tex_names = [] 		# tex_names stores texture handles which are no longer used, and must be deleted
		self.supressInspector = False 	# Suppresses showing the inspector - switched on in emfloatingwidgets
		
		self.coords=[]
		self.nshown=0
		self.valstodisp=["Img #"]
		try: self.parent.setAcceptDrops(True)
		except:	pass

		self.timer = QTimer()
		QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.timeout)

		self.initsizeflag = True
		self.inspector=None
		if data:
			self.setData(data)
	
	def __del__(self):
		if ( len(self.tex_names) > 0 ):	glDeleteTextures(self.tex_names)
		
	def setData(self,data):
		if data == None or not isinstance(data,list) or len(data)==0: return

		if (self.initsizeflag):
			self.initsizeflag = False
			if len(data)<self.nperrow :
				w=len(data)*(data[0].get_xsize()+2)
				hfac = 1
			else : 
				w=self.nperrow*(data[0].get_xsize()+2)
				hfac = len(data)/self.nperrow+1
			hfac *= data[0].get_ysize()
			if hfac > 512:
				hfac = 512
			self.parent.resize(int(w),int(hfac))
			#self.parent.resizeGL(w,hfac)
			

		self.data=data
		if data==None or len(data)==0:
			self.updateGL()
			return
		
		self.nimg=len(data)
		
		self.minden=data[0].get_attr("mean")
		self.maxden=self.minden
		self.mindeng=self.minden
		self.maxdeng=self.minden
		
		for i in data:
			if i.get_zsize()!=1 :
				self.data=None
				self.updateGL()
				return
			mean=i.get_attr("mean")
			sigma=i.get_attr("sigma")
			m0=i.get_attr("minimum")
			m1=i.get_attr("maximum")
		
			self.minden=min(self.minden,max(m0,mean-3.0*sigma))
			self.maxden=max(self.maxden,min(m1,mean+3.0*sigma))
			self.mindeng=min(self.mindeng,max(m0,mean-5.0*sigma))
			self.maxdeng=max(self.maxdeng,min(m1,mean+5.0*sigma))
		
		self.showInspector()		# shows the correct inspector if already open
		#self.timer.start(25)
		

		self.updateGL()
			
		
	def updateGL(self):
		try: self.parent.updateGL()
		except: pass
		
	def setDenRange(self,x0,x1):
		"""Set the range of densities to be mapped to the 0-255 pixel value range"""
		self.minden=x0
		self.maxden=x1
		self.updateGL()
	
	def setOrigin(self,x,y):
		"""Set the display origin within the image"""
		self.origin=(x,y)
		self.targetorigin=None
		self.updateGL()
		
	def setScale(self,newscale):
		"""Adjusts the scale of the display. Tries to maintain the center of the image at the center"""
		
		if self.targetorigin : 
			self.origin=self.targetorigin
			self.targetorigin=None
			
		if self.data and len(self.data)>0 and (self.data[0].get_ysize()*newscale>self.parent.height() or self.data[0].get_xsize()*newscale>self.parent.width()):
			newscale=min(float(self.parent.height())/self.data[0].get_ysize(),float(self.parent.width())/self.data[0].get_xsize())
			if self.inspector: self.inspector.scale.setValue(newscale)
			
			
#		yo=self.height()-self.origin[1]-1
		yo=self.origin[1]
#		self.origin=(newscale/self.scale*(self.width()/2+self.origin[0])-self.width()/2,newscale/self.scale*(self.height()/2+yo)-self.height()/2)
#		self.origin=(newscale/self.scale*(self.width()/2+self.origin[0])-self.width()/2,newscale/self.scale*(yo-self.height()/2)+self.height()/2)
		self.origin=(newscale/self.scale*(self.parent.width()/2+self.origin[0])-self.parent.width()/2,newscale/self.scale*(self.parent.height()/2+self.origin[1])-self.parent.height()/2)
#		print self.origin,newscale/self.scale,yo,self.height()/2+yo
		
		self.scale=newscale
		self.updateGL()
		
	def setDenMin(self,val):
		self.minden=val
		self.updateGL()
		
	def setDenMax(self,val):
		self.maxden=val
		self.updateGL()

	def setGamma(self,val):
		self.gamma=val
		self.updateGL()
	
	def setNPerRow(self,val):
		if self.nperrow==val: return
		if val<1 : val=1
		
		self.nperrow=val
		self.updateGL()
		try:
			if self.inspector.nrow.value!=val :
				self.inspector.nrow.setValue(val)
		except: pass
		
	def setNShow(self,val):
		self.nshow=val
		self.updateGL()

	def setInvert(self,val):
		if val: self.invert=1
		else : self.invert=0
		self.updateGL()
	

	def timeout(self):
		"""Called a few times each second when idle for things like automatic scrolling"""
		if self.targetorigin :
			vec=(self.targetorigin[0]-self.origin[0],self.targetorigin[1]-self.origin[1])
			h=hypot(vec[0],vec[1])
			if h<=self.targetspeed :
				self.origin=self.targetorigin
				self.targetorigin=None
			else :
				vec=(vec[0]/h,vec[1]/h)
				self.origin=(self.origin[0]+vec[0]*self.targetspeed,self.origin[1]+vec[1]*self.targetspeed)
			#self.updateGL()
		
	
	def render(self):

		if not self.data : return
		for i in self.data:
			self.changec[i]=i.get_attr("changecount")
		
		
		
		
		if not self.invert : pixden=(0,255)
		else: pixden=(255,0)
		
#		GL.glPixelZoom(1.0,-1.0)
		n=len(self.data)
		x,y=-self.origin[0],-self.origin[1]
		hist=numpy.zeros(256)
		if len(self.coords)>n : self.coords=self.coords[:n]
		glColor(0.5,1.0,0.5)
		glLineWidth(2)
		try:
			# we render the 16x16 corner of the image and decide if it's light or dark to decide the best way to 
			# contrast the text labels...
			a=self.data[0].render_amp8(0,0,16,16,16,self.scale,pixden[0],pixden[1],self.minden,self.maxden,self.gamma,4)
			ims=[ord(pv) for pv in a]
			if sum(ims)>32768 : txtcol=(0.0,0.0,0.2)
			else : txtcol=(.8,.8,1.0)
		except: txtcol=(1.0,1.0,1.0)

		if ( len(self.tex_names) > 0 ):	glDeleteTextures(self.tex_names)
		self.tex_names = []

		self.nshown=0
		for i in range(n):
			w=int(min(self.data[i].get_xsize()*self.scale,self.parent.width()))
			h=int(min(self.data[i].get_ysize()*self.scale,self.parent.height()))
			#w = self.data[i].get_xsize()*self.scale
			#h = self.data[i].get_ysize()*self.scale
			shown=False
			if x<self.parent.width() and y<self.parent.height() and (x+w) > 0 and (y+h) > 0:
				tx = x
				ty = y
				tw = w
				th = h
				rx = 0	#render x
				ry = 0	#render y
				#print "entry",tx,ty,tw,th,self.parent.width(),self.parent.width()
				if x+tw > self.parent.width():
					tw = int(self.parent.width()-x)
				elif x<0:
					rx = int(-x/self.scale)
					tx = 0
					tw=int(w-tx+x)
					
				if y+th > self.parent.height():
					th = int(self.parent.height()-y)
				elif y<0:
					ry = int(-y/self.scale)
					ty = 0
					th=int(h-ty+y)
	
				shown = True
				#print rx,ry,tw,th,self.parent.width(),self.parent.height()
				if not self.glflags.npt_textures_unsupported():
					a=self.data[i].render_amp8(rx,ry,tw,th,(tw-1)/4*4+4,self.scale,pixden[0],pixden[1],self.minden,self.maxden,self.gamma,2)
					self.texture(a,tx,ty,tw,th)
				else:
					a=self.data[i].render_amp8(rx,ry,tw,th,(tw-1)/4*4+4,self.scale,pixden[0],pixden[1],self.minden,self.maxden,self.gamma,6)
					glRasterPos(tx,ty)
					glDrawPixels(tw,th,GL_LUMINANCE,GL_UNSIGNED_BYTE,a)
						
				if i in self.selected:
					glColor(0.5,0.5,1.0)
					glBegin(GL_LINE_LOOP)
					glVertex(x,y)
					glVertex(x+w,y)
					glVertex(x+w,y+h)
					glVertex(x,y+h)
					glEnd()
				hist2=numpy.fromstring(a[-1024:],'i')
				hist+=hist2
				# render labels

				tagy = y
				glColor(*txtcol)
				for v in self.valstodisp:
					if v=="Img #" : self.renderText(x,tagy,"%d"%i)
					else : 
						av=self.data[i].get_attr(v)
						if isinstance(av,float) : avs="%1.4g"%av
						else: avs=str(av)
						try: self.renderText(x,tagy,str(avs))
						except: self.renderText(x,tagy,"------")
					tagy+=16
				#if x>=0 and y>=0:
					#shown=True
					#a=self.data[i].render_amp8(0,0,w,h,(w-1)/4*4+4,self.scale,pixden[0],pixden[1],self.minden,self.maxden,self.gamma,6)
					#if not self.glflags.npt_textures_unsupported():
						#self.texture(a,x,y,w,h)
					#else:
						#GL.glRasterPos(x,y)
						#GL.glDrawPixels(w,h,GL.GL_LUMINANCE,GL.GL_UNSIGNED_BYTE,a)
					
					# Selection box
					#if i in self.selected:
						#GL.glColor(0.5,0.5,1.0)
						#GL.glBegin(GL.GL_LINE_LOOP)
						#GL.glVertex(x,y)
						#GL.glVertex(x+w,y)
						#GL.glVertex(x+w,y+h)
						#GL.glVertex(x,y+h)
						#GL.glEnd()
					#hist2=numpy.fromstring(a[-1024:],'i')
					#hist+=hist2

					## render labels
					#ty=y
					#GL.glColor(*txtcol)
					#for v in self.valstodisp:
						#if v=="Img #" : self.renderText(x,ty,"%d"%i)
						#else : 
							#av=self.data[i].get_attr(v)
							#if isinstance(av,float) : avs="%1.4g"%av
							#else: avs=str(av)
							#try: self.renderText(x,ty,str(avs))
							#except: self.renderText(x,ty,"------")
						#ty+=16
				#elif x+w>0 and y+h>0:
					#shown=True
					#tx=int(max(x,0))
					#ty=int(max(y,0))
					#tw=int(w-tx+x)
					#th=int(h-ty+y)
					#a=self.data[i].render_amp8(int(-min(x/self.scale,0)),int(-min(y/self.scale,0)),tw,th,(tw-1)/4*4+4,self.scale,pixden[0],pixden[1],self.minden,self.maxden,self.gamma,6)
					#if not self.glflags.npt_textures_unsupported():
						#self.texture(a,tx,ty,tw,th)
					#else:
						#GL.glRasterPos(tx,ty)
						#GL.glDrawPixels(tw,th,GL.GL_LUMINANCE,GL.GL_UNSIGNED_BYTE,a)
				
					#hist2=numpy.fromstring(a[-1024:],'i')
					#hist+=hist2
					
					## Selection box
					#if i in self.selected:
						#GL.glColor(0.5,0.5,1.0)
						#GL.glBegin(GL.GL_LINE_LOOP)
						#GL.glVertex(x,y)
						#GL.glVertex(x+w,y)
						#GL.glVertex(x+w,y+h)
						#GL.glVertex(x,y+h)
						#GL.glEnd()
				
			try: self.coords[i]=(x+self.origin[0],y+self.origin[1],self.data[i].get_xsize()*self.scale,self.data[i].get_ysize()*self.scale,shown)
			except: self.coords.append((x+self.origin[0],y+self.origin[1],self.data[i].get_xsize()*self.scale,self.data[i].get_ysize()*self.scale,shown))
			if shown : self.nshown+=1
			
			if (i+1)%self.nperrow==0 : 
				y+=h+2.0
				x=-self.origin[0]
			else: x+=w+2.0
		
		# If the user is lost, help him find himself again...
		if self.nshown==0 : 
			try: self.targetorigin=(0,self.coords[self.selected[0]][1]-self.parent.height()/2+self.data[0].get_ysize()*self.scale/2)
			except: self.targetorigin=(0,0)
			self.targetspeed=100.0
		
		if self.inspector : self.inspector.setHist(hist,self.minden,self.maxden)
		
	def texture(self,a,x,y,w,h):
		
		tex_name = glGenTextures(1)
		if ( tex_name <= 0 ):
			raise("failed to generate texture name")
		
		width = w/2.0
		height = h/2.0
		
		glPushMatrix()
		glTranslatef(x+width,y+height,0)
			
		glBindTexture(GL_TEXTURE_2D,tex_name)
		glTexImage2D(GL_TEXTURE_2D,0,GL_LUMINANCE,w,h,0,GL_LUMINANCE,GL_UNSIGNED_BYTE, a)
		
		glEnable(GL_TEXTURE_2D)
		glBindTexture(GL_TEXTURE_2D, tex_name)
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
		# using GL_NEAREST ensures pixel granularity
		# using GL_LINEAR blurs textures and makes them more difficult
		# to interpret (in cryo-em)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		# this makes it so that the texture is impervious to lighting
		glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
		
		
		# POSITIONING POLICY - the texture occupies the entire screen area
		glBegin(GL_QUADS)
		
		glTexCoord2f(0,0)
		glVertex2f(-width,height)
		
		glTexCoord2f(1,0)
		glVertex2f(width,height)
			
		glTexCoord2f(1,1)
		glVertex2f(width,-height)
		
		glTexCoord2f(0,1)
		glVertex2f(-width,-height)
			
		glEnd()
		
		glDisable(GL_TEXTURE_2D)
		
		glPopMatrix()
		self.tex_names.append(tex_name)
	
	def renderText(self,x,y,s):
#	        print 'in render Text'
		glRasterPos(x+2,y+2)
		for c in s:
			GLUT.glutBitmapCharacter(GLUT.GLUT_BITMAP_9_BY_15,ord(c))

	
	def resizeEvent(self, width, height):
		
		#print width/(self.data[0].get_xsize()*self.scale)
		if self.data and len(self.data)>0 : self.setNPerRow(int(width/(self.data[0].get_xsize()*self.scale)))
		#except: pass
		
		if self.data and len(self.data)>0 and (self.data[0].get_ysize()*self.scale>self.parent.height() or self.data[0].get_xsize()*self.scale>self.parent.width()):
			self.scale=min(float(self.parent.height())/self.data[0].get_ysize(),float(self.parent.width())/self.data[0].get_xsize())
	
	def isVisible(self,n):
		try: return self.coords[n][4]
		except: return False
	
	def scrollTo(self,n,yonly=0):
		"""Moves image 'n' to the center of the display"""
#		print self.origin,self.coords[0],self.coords[1]
#		try: self.origin=(self.coords[n][0]-self.width()/2,self.coords[n][1]+self.height()/2)
#		try: self.origin=(self.coords[8][0]-self.width()/2-self.origin[0],self.coords[8][1]+self.height()/2-self.origin[1])
		if yonly :
			try: 
				self.targetorigin=(0,self.coords[n][1]-self.parent.height()/2+self.data[0].get_ysize()*self.scale/2)
			except: return
		else:
			try: self.targetorigin=(self.coords[n][0]-self.parent.width()/2+self.data[0].get_xsize()*self.scale/2,self.coords[n][1]-self.parent.height()/2+self.data[0].get_ysize()*self.scale/2)
			except: return
		self.targetspeed=hypot(self.targetorigin[0]-self.origin[0],self.targetorigin[1]-self.origin[1])/20.0
#		print n,self.origin
#		self.updateGL()
	
	def setSelected(self,numlist):
		"""pass an integer or a list/tuple of integers which should be marked as 'selected' in the
		display"""
		if isinstance(numlist,int) : numlist=[numlist]
		if isinstance(numlist,list) or isinstance(numlist,tuple) : self.selected=numlist
		else : self.selected=[]
		self.updateGL()
	
	def setValDisp(self,v2d):
		"""Pass in a list of strings describing image attributes to overlay on the image, in order of display"""
		v2d.reverse()
		self.valstodisp=v2d
		self.updateGL()
	
	def showInspector(self,force=0):
		if (self.supressInspector): return
		if not force and self.inspector==None : return
		self.initInspector()
		self.inspector.show()

	def initInspector(self):
		if not self.inspector : self.inspector=EMImageMxInspector2D(self)
		self.inspector.setLimits(self.mindeng,self.maxdeng,self.minden,self.maxden)

	def scrtoimg(self,vec):
		"""Converts screen location (ie - mouse event) to pixel coordinates within a single
		image from the matrix. Returns (image number,x,y) or None if the location is not within any
		of the contained images. """
		absloc=((vec[0]+self.origin[0]),(self.parent.height()-(vec[1]-self.origin[1])))
		for i,c in enumerate(self.coords):
			if absloc[0]>c[0] and absloc[1]>c[1] and absloc[0]<c[0]+c[2] and absloc[1]<c[1]+c[3] :
				return (i,(absloc[0]-c[0])/self.scale,(absloc[1]-c[1])/self.scale)
		return None
	
	def closeEvent(self,event) :
		if self.inspector: self.inspector.close()
		
	def dragEnterEvent(self,event):
#		f=event.mimeData().formats()
#		for i in f:
#			print str(i)
		
		if event.source()==self:
			event.setDropAction(Qt.MoveAction)
			event.accept()
		elif event.provides("application/x-eman"):
			event.setDropAction(Qt.CopyAction)
			event.accept()

	
	def dropEvent(self,event):
		lc=self.scrtoimg((event.pos().x(),event.pos().y()))
		if event.source()==self:
#			print lc
			n=int(event.mimeData().text())
			if not lc : lc=[len(self.data)]
			if n>lc[0] : 
				self.data.insert(lc[0],self.data[n])
				del self.data[n+1]
			else : 
				self.data.insert(lc[0]+1,self.data[n])
				del self.data[n]
			event.setDropAction(Qt.MoveAction)
			event.accept()
		elif EMAN2.GUIbeingdragged:
			self.data.append(EMAN2.GUIbeingdragged)
			self.setData(self.data)
			EMAN2.GUIbeingdragged=None
		elif event.provides("application/x-eman"):
			x=loads(event.mimeData().data("application/x-eman"))
			if not lc : self.data.append(x)
			else : self.data.insert(lc[0],x)
			self.setData(self.data)
			event.acceptProposedAction()


	def mousePressEvent(self, event):
		lc=self.scrtoimg((event.x(),event.y()))
#		print lc
		if event.button()==Qt.MidButton or (event.button()==Qt.LeftButton and event.modifiers()&Qt.ControlModifier):
			self.showInspector(1)
		elif event.button()==Qt.RightButton or (event.button()==Qt.LeftButton and event.modifiers()&Qt.AltModifier):
			self.mousedrag=(event.x(),event.y())
		elif event.button()==Qt.LeftButton:
			if self.mmode=="drag" and lc:
				xs=int(self.data[lc[0]].get_xsize())
				ys=int(self.data[lc[0]].get_ysize())
				drag = QtGui.QDrag(self.parent)
				mimeData = QtCore.QMimeData()
				mimeData.setData("application/x-eman", dumps(self.data[lc[0]]))
				EMAN2.GUIbeingdragged=self.data[lc[0]]		# This deals with within-application dragging between windows
				mimeData.setText( str(lc[0])+"\n")
				di=QImage(self.data[lc[0]].render_amp8(0,0,xs,ys,xs*4,1.0,0,255,self.minden,self.maxden,1.0,14),xs,ys,QImage.Format_RGB32)
				mimeData.setImageData(QtCore.QVariant(di))
				drag.setMimeData(mimeData)

# This (mini image drag) looks cool, but seems to cause crashing sometimes in the pixmap creation process  :^(
				#di=QImage(self.data[lc[0]].render_amp8(0,0,xs,ys,xs*4,1.0,0,255,self.minden,self.maxden,14),xs,ys,QImage.Format_RGB32)
				#if xs>64 : pm=QtGui.QPixmap.fromImage(di).scaledToWidth(64)
				#else: pm=QtGui.QPixmap.fromImage(di)
				#drag.setPixmap(pm)
				#drag.setHotSpot(QtCore.QPoint(12,12))
				
				dropAction = drag.start()
#				print dropAction
			
			elif self.mmode=="del" and lc:
				del self.data[lc[0]]
				#self.setData(self.data)
				self.updateGL()
			elif self.mmode=="app" and lc:
				self.parent.emit(QtCore.SIGNAL("mousedown"),event,lc)
	
	def mouseMoveEvent(self, event):
		if self.mousedrag:
			self.origin=(self.origin[0]+self.mousedrag[0]-event.x(),self.origin[1]-self.mousedrag[1]+event.y())
			self.mousedrag=(event.x(),event.y())
			self.parent.update()
		elif event.buttons()&Qt.LeftButton and self.mmode=="app":
			self.parent.emit(QtCore.SIGNAL("mousedrag"),event,self.scale)
		
	def mouseReleaseEvent(self, event):
		if self.mousedrag:
			self.mousedrag=None
		elif event.button()==Qt.LeftButton and self.mmode=="app":
			self.parent.emit(QtCore.SIGNAL("mouseup"),event)
			
	def wheelEvent(self, event):
		if event.delta() > 0:
			self.setScale( self.scale * self.mag )
		elif event.delta() < 0:
			self.setScale(self.scale * self.invmag )
		self.resizeEvent(self.parent.width(),self.parent.height())
		# The self.scale variable is updated now, so just update with that
		if self.inspector: self.inspector.setScale(self.scale)
		
	def leaveEvent(self):
		if self.mousedrag:
			self.mousedrag=None

class EMImageMxInspector2D(QtGui.QWidget):
	def __init__(self,target) :
		QtGui.QWidget.__init__(self,None)
		self.target=target
		
		self.vals = QtGui.QMenu()
		self.valsbut = QtGui.QPushButton("Values")
		self.valsbut.setMenu(self.vals)
		
		try:
			self.vals.clear()
			vn=self.target.data[0].get_attr_dict().keys()
			vn.sort()
			for i in vn:
				action=self.vals.addAction(i)
				action.setCheckable(1)
				action.setChecked(0)
		except Exception, inst:
			print type(inst)     # the exception instance
			print inst.args      # arguments stored in .args
			print int
		
		action=self.vals.addAction("Img #")
		action.setCheckable(1)
		action.setChecked(1)
		
		self.vbl = QtGui.QVBoxLayout(self)
		self.vbl.setMargin(2)
		self.vbl.setSpacing(6)
		self.vbl.setObjectName("vboxlayout")
		
		self.hbl3 = QtGui.QHBoxLayout()
		self.hbl3.setMargin(0)
		self.hbl3.setSpacing(6)
		self.hbl3.setObjectName("hboxlayout")
		self.vbl.addLayout(self.hbl3)
		
		self.hist = ImgHistogram(self)
		self.hist.setObjectName("hist")
		self.hbl3.addWidget(self.hist)

		self.vbl2 = QtGui.QVBoxLayout()
		self.vbl2.setMargin(0)
		self.vbl2.setSpacing(6)
		self.vbl2.setObjectName("vboxlayout")
		self.hbl3.addLayout(self.vbl2)

		self.bsavedata = QtGui.QPushButton("Save")
		self.vbl2.addWidget(self.bsavedata)

		self.bsnapshot = QtGui.QPushButton("Snap")
		self.vbl2.addWidget(self.bsnapshot)

		# This shows the mouse mode buttons
		self.hbl2 = QtGui.QHBoxLayout()
		self.hbl2.setMargin(0)
		self.hbl2.setSpacing(6)
		self.hbl2.setObjectName("hboxlayout")
		self.vbl.addLayout(self.hbl2)
		
		#self.mmeas = QtGui.QPushButton("Meas")
		#self.mmeas.setCheckable(1)
		#self.hbl2.addWidget(self.mmeas)

		self.mapp = QtGui.QPushButton("App")
		self.mapp.setCheckable(1)
		self.hbl2.addWidget(self.mapp)
		
		self.mdel = QtGui.QPushButton("Del")
		self.mdel.setCheckable(1)
		self.hbl2.addWidget(self.mdel)

		self.mdrag = QtGui.QPushButton("Drag")
		self.mdrag.setCheckable(1)
		self.mdrag.setDefault(1)
		self.hbl2.addWidget(self.mdrag)

		self.bg=QtGui.QButtonGroup()
		self.bg.setExclusive(1)
#		self.bg.addButton(self.mmeas)
		self.bg.addButton(self.mapp)
		self.bg.addButton(self.mdel)
		self.bg.addButton(self.mdrag)

		self.hbl = QtGui.QHBoxLayout()
		self.hbl.setMargin(0)
		self.hbl.setSpacing(6)
		self.hbl.setObjectName("hboxlayout")
		self.vbl.addLayout(self.hbl)
		
		self.hbl.addWidget(self.valsbut)
		
		self.lbl = QtGui.QLabel("#/row:")
		self.lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
		self.hbl.addWidget(self.lbl)
		
		self.nrow = QtGui.QSpinBox(self)
		self.nrow.setObjectName("nrow")
		self.nrow.setRange(1,50)
		self.nrow.setValue(self.target.nperrow)
		self.hbl.addWidget(self.nrow)
		
		self.scale = ValSlider(self,(0.1,5.0),"Mag:")
		self.scale.setObjectName("scale")
		self.scale.setValue(1.0)
		self.vbl.addWidget(self.scale)
		
		self.mins = ValSlider(self,label="Min:")
		self.mins.setObjectName("mins")
		self.vbl.addWidget(self.mins)
		
		self.maxs = ValSlider(self,label="Max:")
		self.maxs.setObjectName("maxs")
		self.vbl.addWidget(self.maxs)
		
		self.brts = ValSlider(self,(-1.0,1.0),"Brt:")
		self.brts.setObjectName("brts")
		self.vbl.addWidget(self.brts)
		
		self.conts = ValSlider(self,(0.0,1.0),"Cont:")
		self.conts.setObjectName("conts")
		self.vbl.addWidget(self.conts)
		
		self.gammas = ValSlider(self,(.5,2.0),"Gam:")
		self.gammas.setObjectName("gamma")
		self.gammas.setValue(1.0)
		self.vbl.addWidget(self.gammas)

		self.lowlim=0
		self.highlim=1.0
		self.busy=0
		
		QtCore.QObject.connect(self.vals, QtCore.SIGNAL("triggered(QAction*)"), self.newValDisp)
		QtCore.QObject.connect(self.nrow, QtCore.SIGNAL("valueChanged(int)"), target.setNPerRow)
		QtCore.QObject.connect(self.scale, QtCore.SIGNAL("valueChanged"), target.setScale)
		QtCore.QObject.connect(self.mins, QtCore.SIGNAL("valueChanged"), self.newMin)
		QtCore.QObject.connect(self.maxs, QtCore.SIGNAL("valueChanged"), self.newMax)
		QtCore.QObject.connect(self.brts, QtCore.SIGNAL("valueChanged"), self.newBrt)
		QtCore.QObject.connect(self.conts, QtCore.SIGNAL("valueChanged"), self.newCont)
		QtCore.QObject.connect(self.gammas, QtCore.SIGNAL("valueChanged"), self.newGamma)
		
		#QtCore.QObject.connect(self.mmeas, QtCore.SIGNAL("clicked(bool)"), self.setMeasMode)
		QtCore.QObject.connect(self.mapp, QtCore.SIGNAL("clicked(bool)"), self.setAppMode)
		QtCore.QObject.connect(self.mdel, QtCore.SIGNAL("clicked(bool)"), self.setDelMode)
		QtCore.QObject.connect(self.mdrag, QtCore.SIGNAL("clicked(bool)"), self.setDragMode)

		QtCore.QObject.connect(self.bsavedata, QtCore.SIGNAL("clicked(bool)"), self.saveData)
		QtCore.QObject.connect(self.bsnapshot, QtCore.SIGNAL("clicked(bool)"), self.snapShot)
	
	def setScale(self,val):
		if self.busy : return
		self.busy=1
		self.scale.setValue(val)
		self.busy=0
	
	def saveData(self):
		if self.target.data==None or len(self.target.data)==0: return

		# Get the output filespec
		fsp=QtGui.QFileDialog.getSaveFileName(self, "Select File","","","",QtGui.QFileDialog.DontConfirmOverwrite)
		fsp=str(fsp)
		
		# if the file exists, ask the user what to do
		if QtCore.QFile.exists(fsp) :
			ow = QtGui.QMessageBox.question(self,"Overwrite or Append","Do you wish to overwrite\nthe existing file (Discard) or\nappend images to the end (Ok)  ?",
				QtGui.QMessageBox.Discard,QtGui.QMessageBox.Ok,QtGui.QMessageBox.Cancel)
			if ow == QtGui.QMessageBox.Cancel : return
			if ow == QtGui.QMessageBox.Discard :
				QtCore.QFile.remove(fsp)
				# for IMAGIC files, make sure we remove the image data and the header
				if fsp[-4:]==".hed" : QtCore.QFile.remove(fsp[:-4]+".img")
				if fsp[-4:]==".HED" : QtCore.QFile.remove(fsp[:-4]+".IMG")
				if fsp[-4:]==".img" : QtCore.QFile.remove(fsp[:-4]+".hed")
				if fsp[-4:]==".IMG" : QtCore.QFile.remove(fsp[:-4]+".HED")
		
		for i in self.target.data:
#			try:
				i.write_image(fsp,-1)
#			except:
#				QtGui.QMessageBox.warning ( self, "File write error", "One or more images were not sucessfully written to '%s'"%fsp)
#				break
			
	def snapShot(self):
		"Save a screenshot of the current image display"
		
		try:
			qim=self.target.grabFrameBuffer()
		except:
			QtGui.QMessageBox.warning ( self, "Framebuffer ?", "Could not read framebuffer")
		
		# Get the output filespec
		fsp=QtGui.QFileDialog.getSaveFileName(self, "Select File")
		fsp=str(fsp)
		
		qim.save(fsp,None,90)
		
	def newValDisp(self):
		v2d=[str(i.text()) for i in self.vals.actions() if i.isChecked()]
		self.target.setValDisp(v2d)

	def setAppMode(self,i):
		self.target.mmode="app"
	
	def setMeasMode(self,i):
		self.target.mmode="meas"
	
	def setDelMode(self,i):
		self.target.mmode="del"
	
	def setDragMode(self,i):
		self.target.mmode="drag"

	def newMin(self,val):
		if self.busy : return
		self.busy=1
		self.target.setDenMin(val)

		self.updBC()
		self.busy=0
		
	def newMax(self,val):
		if self.busy : return
		self.busy=1
		self.target.setDenMax(val)
		self.updBC()
		self.busy=0
	
	def newBrt(self,val):
		if self.busy : return
		self.busy=1
		self.updMM()
		self.busy=0
		
	def newCont(self,val):
		if self.busy : return
		self.busy=1
		self.updMM()
		self.busy=0
	
	def newGamma(self,val):
		if self.busy : return
		self.busy=1
		self.target.setGamma(val)
		self.busy=0

	def updBC(self):
		b=0.5*(self.mins.value+self.maxs.value-(self.lowlim+self.highlim))/((self.highlim-self.lowlim))
		c=(self.mins.value-self.maxs.value)/(2.0*(self.lowlim-self.highlim))
		self.brts.setValue(-b)
		self.conts.setValue(1.0-c)
		
	def updMM(self):
		x0=((self.lowlim+self.highlim)/2.0-(self.highlim-self.lowlim)*(1.0-self.conts.value)-self.brts.value*(self.highlim-self.lowlim))
		x1=((self.lowlim+self.highlim)/2.0+(self.highlim-self.lowlim)*(1.0-self.conts.value)-self.brts.value*(self.highlim-self.lowlim))
		self.mins.setValue(x0)
		self.maxs.setValue(x1)
		self.target.setDenRange(x0,x1)
		
	def setHist(self,hist,minden,maxden):
		self.hist.setData(hist,minden,maxden)

	def setLimits(self,lowlim,highlim,curmin,curmax):
		self.lowlim=lowlim
		self.highlim=highlim
		self.mins.setRange(lowlim,highlim)
		self.maxs.setRange(lowlim,highlim)
		self.mins.setValue(curmin)
		self.maxs.setValue(curmax)

# This is just for testing, of course
if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	GLUT.glutInit("")
	window = EMImageMX()
	if len(sys.argv)==1 : window.setData([test_image(),test_image(1),test_image(2),test_image(3)])
	else :
		a=EMData.read_images(sys.argv[1])
		window.setData(a)
	window2=EMParentWin(window)
	window2.show()
	
#	w2=QtGui.QWidget()
#	w2.resize(256,128)
	
#	w3=ValSlider(w2)
#	w3.resize(256,24)
#	w2.show()
	
	sys.exit(app.exec_())

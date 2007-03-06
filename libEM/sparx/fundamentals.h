/**
 * $Id$
 */

/*
 * Author: Pawel A.Penczek, 09/09/2006 (Pawel.A.Penczek@uth.tmc.edu)
 * Copyright (c) 2000-2006 The University of Texas - Houston Medical School
 *
 * This software is issued under a joint BSD/GNU license. You may use the
 * source code in this file under either license. However, note that the
 * complete EMAN2 and SPARX software packages have some GPL dependencies,
 * so you are responsible for compliance with the licenses of these packages
 * if you opt to use BSD licensing. The warranty disclaimer below holds
 * in either instance.
 *
 * This complete copyright notice must be included in any revised version of the
 * source code. Additional authorship citations may be added, but existing
 * author citations must be preserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 */

#ifndef eman_fundamentals_h
#define eman_fundamentals_h

#include <cstddef>


/** @file fundamentals.h
 *  Image Fundamentals -- 
 *  Loose collection of fundamental image processing tools.
 *  @author P. A. Penczek <Pawel.A.Penczek@uth.tmc.edu>.
 *  The University of Texas.
 *  Please do not modify the contents of this document
 *  without written consent of the author.
 *
 *  @date $Date$
 *
 *  @see H.R. Myler and A.R. Weeks, "The Pocket Handbook of
 *  Image Processing Algorithms in C" (Prentice Hall, 
 *  Upper Saddle River, 1993), p. 129.
 */

namespace EMAN
{
	class EMData;
	/** Fourier Product processing flag.
	 *  Should the Fourier data be treated as manifestly 
	 *  periodic (CIRCULANT), padded with zeros (PADDED),
	 *  or padded with a lag (PADDED_LAG).  Also, in each of
	 *  these cases the product may be normalized or not.
	 *  Pick one, as there is no default.
	 */
	enum fp_flag {
		CIRCULANT = 1,
		CIRCULANT_NORMALIZED = 2,
		PADDED = 3,
		PADDED_NORMALIZED = 4,
		PADDED_LAG = 5,
		PADDED_NORMALIZED_LAG = 6
	};
	EMData* self_correlation(EMData* f, fp_flag myflag);
	// You probably don't need to use these next two directly.
	enum fp_type {
		CORRELATION,
		CONVOLUTION,
		SELF_CORRELATION,
		AUTOCORRELATION
	};
	/** Fourier product of two images.
	 *
	 * @par Purpose: Calculate the correlation or convolution of
	 *               two images, or the autocorrelation or 
	 *               self-correlation of one image.
	 *
	 *  
	 *  @param[in] f First image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] g Second image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  The size of g must be the
	 *               same as the size of f.  Image g is not changed.
	 *  @param[in] myflag Processing flag (see above).
	 *  @param[in] mytype Type of Fourier product to perform. (see above).
	 *
	 *  @return 1-, 2-, or 3-dimensional real fourier product image.
	 */
	EMData* fourierproduct(EMData* f, EMData* g, fp_flag myflag,
			fp_type mytype);
	/** Correlation of two images.
	 *
	 * @par Purpose: Calculate the correlation of two 1-, 2-,
	 *               or 3-dimensional images.
	 * @par Method: This function calls fourierproduct.
	 *  
	 *  @param[in] f First image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] g Second image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  The size of g must be the
	 *               same as the size of f.  Image g is not changed.
	 *  @param[in] myflag Processing flag (see above).
	 *
	 *  @return Real-space correlation image.
	 */
	inline EMData* correlation(EMData* f, EMData* g, fp_flag myflag) {
		return fourierproduct(f, g, myflag, CORRELATION);
	}
	/** Convolution of two images.
	 *
	 * @par Purpose: Calculate the convolution of two 1-, 2-,
	 *               or 3-dimensional images.
	 * @par Method: This function calls fourierproduct.
	 *  
	 *  @param[in] f First image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] g Second image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  The size of g must be the
	 *               same as the size of f.  Image g is not changed.
	 *  @param[in] myflag Processing flag (see above).
	 *
	 *  @return Real-space convolution image.
	 */
	inline EMData* convolution(EMData* f, EMData* g, fp_flag myflag) {
		return fourierproduct(f, g, myflag, CONVOLUTION);
	}
	/** Real-space convolution of two images.
	 *
	 * @par Purpose: Calculate the convolution of two 1-, 2-,
	 *               or 3-dimensional images.
	 *  
	 *  @param[in] f First real-space image object.
	 *               Image may be 1-, 2-, or 3-dimensional.  Image f is not
	 *               changed.
	 *  @param[in] K Second real-space image object (the convolution Kernel).
	 *               Image may be 1-, 2-, or 3-dimensional.  Image K is not changed.
	 *
	 *  @return Real-space convolution image.
	 */
	EMData* rsconvolution(EMData* f, EMData* K);
	/** Real-space convolution with the K-B window.
	 *
	 * @par Purpose: Calculate the convolution with the K-B window.
	 *  
	 *  @param[in] f First real-space image object.
	 *               Image may be 1-, 2-, or 3-dimensional.  Image f is not
	 *               changed.
	 *  @return Real-space convolution image.
	 */
	EMData* rscp(EMData* f);
	/** Image autocorrelation.
	 *
	 * @par Purpose: Calculate the autocorrelation of a 1-, 2-,
	 *               or 3-dimensional image.
	 * @par Method: This function calls fourierproduct.
	 *
	 *  
	 *  @param[in] f Image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] myflag Processing flag (see above).
	 *
	 *  @return Real-space autocorrelation image.
	 */
	inline EMData* autocorrelation(EMData* f, fp_flag myflag) {
		return fourierproduct(f, NULL, myflag, AUTOCORRELATION);
	}
	/** Image self-c			// incommensurate sizes
			throw ImageDimensionException("input images are incommensurate");
orrelation.
	 *
	 * @par Purpose: Calculate the self-correlation of a 1-, 2-,
	 *               or 3-dimensional image.
	 * @par Method: This function calls fourierproduct.
	 *
	 *  This function actually calls fourierproduct.
	 *  
	 *  @param[in] f Image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] myflag Processing flag (see above).
	 *
	 *  @return Real-space self-correlation image.
	 */
	inline EMData* self_correlation(EMData* f, fp_flag myflag) {
		return fourierproduct(f, NULL, myflag, SELF_CORRELATION);
	}
	/** Image periodogram.
	 *
	 * @par Purpose: Calculate a periodogram (a squared modulus of
	 *               the Fourier Transform) of a 1-, 2-, 
	 *               or 3-dimensional image.
	 * @par Method: Calculate FFT (if needed), squared modulus,
	 *              shift the origin to \f$n/2 + 1$\f, and 
	 *              create the Friedel-related part.
	 *
	 *  @param[in] f Image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *
	 *  @return 1-, 2-, or 3-D real image containing the periodogram.
	 *          F(0,0,0)^2 is at the image center.
	 */
	EMData* periodogram(EMData* f);
	/** Normalize, pad, and Fourier transform convenience function.
	 *
	 * @par Purpose: Create a new [normalized] [zero-padded] Fourier image.
	 *
	 * @par Method: Normalize (if requested), pad with zeros (if 
	 *      requested), extend along x for fft, create new fft image,
	 *      and return the new fft image.
	 *
	 *  @param[in] f Real-space image object.
	 *               Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] do_norm If true then perform normalization.
	 *  @param[in] do_pad If true then perform zero-padding.
	 *  @param[in] npad   Amount of zero-padding to use (defaults to 2 if do_pad is true).
	 *
	 *  @return fft image of [normalized,] [zero-padded] input image.
	 */
	EMData* norm_pad_ft(EMData* f, bool do_norm, bool do_pad, int npad = 2);
	/** Do two images have the same size?
	 *
	 * @warning The current function is too stupid.  It needs to 
	 *          be able to compare real-space and Fourier images
	 *          appropriately.
	 *
	 * @par Purpose: Determine if two images have equal sizes.
	 *
	 *  @param[in] f First image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image f is not changed.
	 *  @param[in] g Second image object, either a real-space image
	 *               or a Fourier image.  Image may be 1-, 2-,
	 *               or 3-dimensional.  Image g is not changed.
	 *
	 *  @return true if the images have the same size, false otherwise.
	 */
	bool    equalsize(EMData* f, EMData* g);

	enum kernel_shape {
		BLOCK = 1,
		CIRCULAR = 2,
		CROSS = 3
	};

	EMData* filt_median(EMData* f, int kernel_size, kernel_shape myshape);
	/** Median filter
	 *
	 * @par Purpose: Calculate the median filtered image.
	 *  
	 *  @param[in] f First real-space image object.
	 *               Image may be 1-, 2-, or 3-dimensional.  Image f is not
	 *               changed.
	 *  @param[in] kernel_size Size of the kernal, should be odd.
	 *             For block kernal, this is the edge length of the line/square/cube;
	 *             For circular kernal, this is the diameter of the line/circle/sphere;
	 *             For cross kernal, this is the length of the line/cross;
	 *  	       It should be noted that for 1-dimensional image, these 
	 *  	       three kernels degenerate into the same shape.
	 *  @param[in] myshape     Shape of the kernal
	 *  	       BLOCK is for block kernal;
	 *  	       CIRCULAR is for circular kernel;
	 *  	       CROSS is for cross kernal;
	 *  	       It should be noted that for 1-dimensional image, these 
	 *  	       three kernels degenerate into the same shape.
	 *  @return Median filtered image.
	 */
}


#endif // eman_fundamentals_h

/* vim: set ts=4 noet: */

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A module to find any layers in a molecular structure
"""
import numpy as np
import pandas as pd	
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from src.calc import general_calc as gen_calc
from src.calc import molecule_utils as mol_utils
from src.calc import geometry as geom


class Molecular_Layers(gen_calc.Calc_Type):
	"""
	Will get the distribution of couplings from hamiltonian data for each predefined layer. 
	"""
	required_data_types = ('pos', )
	required_calc = ("long_ax_rotation", )
	_defaults = {'allow_boundaries': False, "plot_layers": False, 'rotate_to_long_axis': False}
	required_metadata = ("atoms_per_molecule", 'rotate_to_long_axis', )
	metadata = {'file_type': 'json'}
	name = "Molecular Layers"

	def _calc_(self):
		"""
		Will calculate the couplings in each layer.

		This works by first 
		"""
		self.ats_per_mol = self.metadata
		# Get the xyz data
		xyz_data = self.Var.data.get_xyz_data()
		cols = self.Var.data.get_xyz_cols()


		for ifile in range(len(xyz_data)):
			for istep in range(len(xyz_data[ifile])):
				step_data = xyz_data[ifile][istep]
				cols = cols[ifile][istep]

				mol_crds = mol_utils.atoms_to_mols(step_data, self.metadata['atoms_per_molecule'])
				mol_col = mol_utils.cols_to_mols(cols, self.metadata['atoms_per_molecule'])

				COM = mol_utils.get_COM_split_mols(mol_crds, mol_col)
				if self.metadata['rotate_to_long_axis']:	 self.rotated_COM = geom.rotate_crds(COM, self.long_ax_rotation.xy_rotation_matrix)
				else:						 self.rotated_COM = COM

				self.sys_info = geom.get_system_size_info(self.rotated_COM)

				self.layer_starts = self.get_layers(self.rotated_COM)
				self.nlayers = len(self.layer_starts)
				self.layer_mols, self.layer_inds = self.get_layer_mols(self.rotated_COM)

				if self.metadata['plot_layers'] is True:
					self.plot_layers()
					plt.show()

	def get_layer_mols(self, mols):
		"""
		Will get the molecules in each layer.

		Inputs:
			* mols <array> => The molecules in the system.
		Outputs:
			* <list> The molecules arranged into layers
		"""
		# Get those mols before the first layer boundary
		mask = mols[:, 2] < self.layer_starts[0]
		all_inds = np.arange(len(mols))

		layer_mols = [mols[mask]]
		layer_inds = [all_inds[mask]]

		# Get mols in between layers
		for ilayer in range(len(self.layer_starts)-1):
			start, end = self.layer_starts[ilayer], self.layer_starts[ilayer+1]
			mask = (mols[:, 2] < end) & (mols[:, 2] > start)

			layer_mols.append(mols[mask])
			layer_inds.append(all_inds[mask])

		# Get the rest of the mols
		mask = mols[:, 2] > self.layer_starts[-1]
		layer_mols.append(mols[mask])
		layer_inds.append(all_inds[mask])

		return layer_mols, layer_inds


	def get_layers(self, xyz):
		"""
		Will find the layers in the system.

		Inputs:
			* xyz <arr> => The pos array of shape (N, 3)
		
		Outputs:
			<list> The start position of each layer.
		"""
		# Scan across the system and find the layer structure.
		self.z, self.num = [], []
		init_z = np.linspace(self.sys_info['zmin'], self.sys_info['zmax'], 500)
		for zmin in init_z:
			mask = (xyz[:, 2] > zmin) & (xyz[:, 2] < zmin + 4)
			self.z.append(zmin)
			self.num.append(sum(mask))

		# Smooth the data
		self.smoothed_df = pd.DataFrame({'num': self.num, 'z': self.z})
		self.smoothed_df = self.smoothed_df.rolling(15, center=True).mean().dropna()
		# self.smoothed_df['gradient'] = np.abs(self.smoothed_df['num'] - np.roll(self.smoothed_df['num'], 10))
		self.smoothed_df.index = np.arange(len(self.smoothed_df))


		# Get some starting points for the minima
		max_data, min_data = np.max(self.smoothed_df['num']), np.min(self.smoothed_df['num'])
		data_range = max_data - min_data

		# Use a steepest descent-eqsue algorithm to get true local minima
		true_min = []
		for i in np.linspace(self.sys_info['zmin'], self.sys_info['zmax'], 100):
			z_ind = self.smoothed_df.index[np.argmin(np.abs(self.smoothed_df['z'] - i))]

			new_ind, _ = geom.find_local_min(self.smoothed_df['num'], z_ind, self.metadata['allow_boundaries'])

			if new_ind is not False:
				true_min.append(self.smoothed_df.loc[new_ind, 'z'])

		_, true_min = geom.cluster_1D_points(true_min, np.diff(init_z)[0]*0.2)

		return true_min

	def plot_layers(self):
		"""
		"""
		f = plt.figure()
		a2D = f.add_subplot(121)
		a3D = f.add_subplot(122, projection="3d")
		
		a3D.set_xlabel("X"); a3D.set_ylabel("Y"); a3D.set_zlabel("Z");
		a3D.set_xticks([]);  a3D.set_yticks([]);  a3D.set_zticks([]);

		a3D.view_init(elev=-3, azim=64)
		for i in self.layer_mols:
			self._plot_xyz_data(i, a3D)

		a2D.plot(self.z, self.num)
		a2D.plot(self.smoothed_df['z'], self.smoothed_df['num'], 'k--', alpha=0.5)

		for i in self.layer_starts:
			a2D.axvline(i, ls='--', color='k', lw=1)
		
		a2D.set_ylabel("Mol Count")
		a2D.set_xlabel(r"Z [$\AA$]")
		
		plt.tight_layout()
		return a2D
		
	def json_data(self):
		"""
		Will return the json data
		"""
		write_data =  {
			   		    'nmol': len(self.layer_inds),
			   		    'layer_starts': self.layer_starts.tolist(),
			   		  }
		for i in range(len(self.layer_inds)):
			write_data[f'layer_{i}'] = {
						  				'mol_inds': self.layer_inds[i].tolist()
									   }

		return write_data
	

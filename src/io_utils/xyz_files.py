#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 11:32:22 2019

A module containing methods relevant to xyz files.

To read an xyz file use the function `read_xyz_file(filepath <str>)`

To write an xyz file use the function `write_xyz_file(xyz_data <np.array | list>, filepath <str>)`
"""

import re
import os
import difflib as dfl
from collections import OrderedDict
import numpy as np
from scipy.stats import mode

from src.io_utils import general_io as gen_io
from src.utils import type_checking as type_check


class XYZ_File(object):
    """
    A container to store xyz data in.

    This class will store data from an xyz file and also overload the in_built
    mathematical operators e.g. adding, subtracting, multiplying etc... to allow
    easy manipulation of the data without loosing any metadata.

    Inputs/Attributes:
        * xyz <numpy.array> => The parsed xyz data from an xyz file.
        * cols <numpy.array> => The parsed column data from the xyz file.
        * timesteps <numpy.array> => The parsed timesteps from the xyz file.

        # * write_precision <int> => The precision with which to write the data.
    """
    # write_precision = 5
    def __init__(self, xyz, cols, timesteps):
        self.xyz = np.array(xyz)
        self.cols = np.array(cols)
        self.timesteps = np.array(timesteps)

        self.nstep = len(self.xyz)
        self.natom = self.xyz.shape[1]
        self.ncol = self.xyz.shape[2]

    # Overload adding
    def __add__(self, val):
        self.xyz += val
        return self
    # Overload multiplying
    def __mul__(self, val):
        self.xyz *= val
        return self
    # Overload subtracting
    def __sub__(self, val):
        self.xyz -= val
        return self
    # Overload division operator i.e. a / b
    def __truediv__(self, val):
        self.xyz /= val
        return self
    # Overload floor division operator i.e. a // b
    def __floordiv__(self, val):
        self.xyz //= val
        return self
    # Overload the power operator
    def __pow__(self, val):
        self.xyz **= val
        return self
    # Overload the str function (useful for writing files).
    def __str__(self):
        # Create an array of spaces/newlines to add between data columns in str
        space = ["    "] * self.natom

        # Convert floats to strings (the curvy brackets are important for performance here)
        xyz = self.xyz.astype(str)
        xyz = (['    '.join(line) for line in step_data] for step_data in xyz)
        cols = np.char.add(self.cols[0], space)
        head_str = '%i\ntime = ' % self.natom
        s = (head_str + ("%.3f\n" % t) + '\n'.join(np.char.add(cols, step_data)) + "\n"
             for step_data, t in zip(xyz, self.timesteps))

        # Create the str
        return ''.join(s)


def write_xyz_file(XYZ_Data, filepath=False):
    """
    Will write 1 xyz file from an XYZ_File object.

    Inputs:
        * XYZ_Data => An XYZ_File object -the output of the 'read_xyz_file' fnc.
        * filepath => The path to the file to be written to.
    Outputs:
        <str> The output string to be written.
    """
    fileTxt = str(XYZ_Data)
    if filepath is not False:
        with open(filepath, "w") as f:
            f.write(fileTxt)


def string_between(Str, substr1, substr2):
    """
    Returns the string between 2 substrings within a string e.g. the string between A and C in 'AbobC' is bob.

    Inputs:
      * line <str> => A line from the xyz file

    Outputs:
      <str> The string between 2 substrings within a string.
    """
    Str = Str[Str.find(substr1)+len(substr1):]
    Str = Str[:Str.find(substr2)]
    return Str

def is_atom_line(line):
    """
    Checks if a line of text is an atom line in a xyz file

    Inputs:
      * line <str> => A line from the xyz file

    Outputs:
      <bool> Whether the line contains atom data
    """
    words = line.split()
    # If the line is very short it isn't a data line
    if not len(words):
        return False

    # Check to see how many float there are compared to other words
    fline = [len(re.findall("[0-9]\.[0-9]", i)) > 0 for i in words]
    percentFloats = fline.count(True) / float(len(fline))
    if percentFloats < 0.5:
        return False
    else:
        return True


def num_atoms_find(ltxt):
    """
    Will determine the number of atoms in an xyz file

    Inputs:
       * ltxt <list<str>> => A list with every line of the input file as a different element.

    Outputs:
       <tuple<int>> The line which the atom data starts and how many atom data lines there are.
    """
    start_atoms, finish_atoms = 0,0
    for i,line in enumerate(ltxt):
        if (is_atom_line(line)) == True:
            start_atoms = i
            break
    else:
        print("Start of atom lines = %i" % start_atoms)
        raise SystemExit("Can't read this xyz file! I can't find where the atom section starts!")

    for i,line in enumerate(ltxt[start_atoms:]):
        if (is_atom_line(line) == False):
            finish_atoms=i
            break
    else:
        finish_atoms = len(ltxt[start_atoms:])

    return start_atoms, finish_atoms


# Finds the number of title lines and number of atoms with a step
def find_num_title_lines(step): # should be the text in a step split by line
    """
    Finds the number of title lines and number of atoms with a step

    Inputs:
       * step <list<str>> => data of 1 step in an xyz file.

    Outputs:
       <int> The number of lines preceeding the data section in an xyz file.
    """
    num_title_lines = 0
    for line in step:
        if is_atom_line(line):
            break
        num_title_lines += 1

    return num_title_lines


# Finds the delimeter for the time-step in the xyz_file title
def find_time_delimeter(step, filename):
    """
    Will find the delimeter for the timestep in the xyz file title.

    Inputs:
       * step <list<str>> => data of 1 step in an xyz file.
       * filename <str> => the name of the file (only used for error messages)

    Outputs:
       <str> The time delimeter used to signify the timestep in the xyz file.
    """
    # Check to see if we can find the word time in the title lines.
    for linenum, txt in enumerate(step):
        txt = txt.lower()
        if 'time' in txt:
            break
    else:
        return [False] * 2

    # find the character before the first number after the word time.
    prev_char, count = False, 0
    txt = txt[txt.find("time"):]
    for char in txt.replace(" ",""):
        isnum = (char.isdigit() or char == '.')
        if isnum != prev_char:
            count += 1
        prev_char = isnum
        if count == 2:
            break
    if char.isdigit(): return '\n', linenum
    else: return char, linenum
    return [False] * 2


def get_num_data_cols(ltxt, filename, num_title_lines, lines_in_step):
    """
    Will get the number of columns in the xyz file that contain data. This isn't a foolproof method
    so if there are odd results maybe this is to blame.

    Inputs:
        * ltxt <list<str>> => A list with every line of the input file as a different element.
        * filename <str> => The path to the file that needs opening
        * num_title_lines <int> => The number of non-data lines
        * lines_in_step <int> => How many lines in 1 step of the xyz file
    Outputs:
        <int> The number of columns in the data section.
    """
    dataTxt = [ltxt[num_title_lines + (i*lines_in_step) : (i+1)*lines_in_step]
               for i in range(len(ltxt) // lines_in_step)]

    num_data_cols_all = []
    for step in dataTxt[:20]:
       for line in step:
          splitter = line.split()
          count = 0
          for item in splitter[-1::-1]:
             if not type_check.is_float(item):
                num_data_cols_all.append(count)
                break
             count += 1

    num_data_cols = mode(num_data_cols_all)[0][0]
    return num_data_cols


# Will get necessary metadata from an xyz file such as time step_delim, lines_in_step etc...
# This will also create the step_data dictionary with the data of each step in
def get_xyz_metadata(filename, ltxt=False):
    """
    Get metadata from an xyz file.

    This function is used in the reading of xyz files and will retrieve data necessary for reading
    xyz files.

    Inputs:
       * filename <str> => the path to the file that needs parsing
       * ltxt <list<str>> OPTIONAL => the parsed txt of the file with each line in a separate element.

    Outputs:
       <dict> A dictionary containing useful parameters such as how many atom lines, how to get the timestep, num of frames.
    """
    if ltxt == False:
        ltxt = gen_io.open_read(filename).split('\n')
    # Check whether to use the very stable but slow parser or quick slightly unstable one
    most_stable = False
    if any('**' in i for i in ltxt[:300]):
        most_stable = True

    if not most_stable:
        num_title_lines, num_atoms = num_atoms_find(ltxt)
        lines_in_step = num_title_lines + num_atoms
        if len(ltxt) > lines_in_step+1: # take lines from the second step instead of first as it is more reliable
           step_data = {i: ltxt[i*lines_in_step:(i+1)*lines_in_step] for i in range(1,2)}
        else: #If there is no second step take lines from the first
           step_data = {1:ltxt[:lines_in_step]}
    else:
        lines_in_step = find_num_title_lines(ltxt, filename)
        step_data = {i: ltxt[i*lines_in_step:(i+1)*lines_in_step] for i in range(1,2)}
        num_title_lines = find_num_title_lines(step_data[1])

    nsteps = int(len(ltxt)/lines_in_step)
    time_delim, time_ind = find_time_delimeter(step_data[1][:num_title_lines],
                                               filename)
    num_data_cols = get_num_data_cols(ltxt, filename, num_title_lines, lines_in_step)
    return {'time_delim': time_delim,
            'time_ind': time_ind,
            'lines_in_step': lines_in_step,
            'num_title_lines': num_title_lines,
            'num_data_cols': num_data_cols,
            'nsteps': nsteps}


def splitter(i):
    """
    Splits each string in a list of strings.
    """
    return [j.split() for j in i]


def read_xyz_file(filename, num_data_cols=False,
                  min_time=0, max_time='all', stride=1,
                  ignore_steps=[], metadata=False):
    """
    Will read 1 xyz file with a given number of data columns.

    Inputs:
        * filename => the path to the file to be read
        * num_data_cols => the number of columns which have data (not metadata)
        * min_time => time to start reading from
        * max_time => time to stop reading at
        * stride => what stride to take when reading
        * ignore_steps => a list of any step numbers to ignore.
        * metadata => optional dictionary containing the metadata

    Outputs:
        * data, cols, timesteps = the data, metadata and timesteps respectively
    """
    # Quick type check of param fed into the func
    if type(stride) != int and isinstance(min_step, (int, float)):
            print("min_time = ", min_time, " type = ", type(min_time))
            print("max_time = ", max_time, " type = ", type(max_time))
            print("stride = ", stride, " type = ", type(stride))
            raise SystemExit("Input parameters are the wrong type!")

    # Get bits of metadata
    if num_data_cols is not False:
       num_data_cols = -num_data_cols
    ltxt = [i for i in gen_io.open_read(filename).split('\n') if i]
    if metadata is False:
        metadata = get_xyz_metadata(filename, ltxt)
        if num_data_cols is False:
           num_data_cols = -metadata['num_data_cols']
    lines_in_step = metadata['lines_in_step']
    num_title_lines = metadata['num_title_lines']
    get_timestep = metadata['time_ind'] is not False
    if get_timestep:
       time_ind = metadata['time_ind']
       time_delim = metadata['time_delim']
    num_steps = metadata['nsteps']

    # Ignore any badly written steps at the end
    badEndSteps = 0
    for i in range(num_steps, 0, -1):
      stepData = ltxt[(i-1)*lines_in_step:(i)*lines_in_step][num_title_lines:]
      badStep = False
      for line in stepData:
         if '*********************' in line:
            badEndSteps += 1
            badStep = True
            break
      if badStep is False:
         break


    # The OrderedDict is actually faster than a list here.
    #   (time speedup at the expense of space)
    step_data = OrderedDict()  # keeps order of frames -Important
    all_steps = [i for i in range(0, num_steps-badEndSteps, stride)
                 if i not in ignore_steps]

    # Get the timesteps
    if get_timestep:
       timelines = [ltxt[time_ind+(i*lines_in_step)] for i in all_steps]
       timesteps = [string_between(line, "time = ", time_delim)
                    for line in timelines]
       timesteps = np.array(timesteps)
       timesteps = timesteps.astype(float)
    else:
       print("***********WARNING***************\n\nThe timesteps could not be extracted\n\n***********WARNING***************")
       timesteps = [0] * len(all_steps)

    # Get the correct steps (from min_time and max_time)
    all_steps = np.array(all_steps)
    if get_timestep:
       mask = timesteps >= min_time
       if type(max_time) == str:
         if 'all' not in max_time.lower():
            msg = "You inputted max_time = `%s`\n" % max_time
            msg += "Only the following are recognised as max_time parameters:\n\t*%s" % '\n\t*'.join(['all'])
            print(msg)
            raise SystemExit("Unknown parameter for max_time.\n\n"+msg)
       else:
         mask = mask & (timesteps <= max_time)
       all_steps = all_steps[mask]
       timesteps = timesteps[mask]

    # Get the actual data (but only up to the max step)
    min_step, max_step = min(all_steps), max(all_steps)+1
    all_data = np.array(ltxt)[min_step*metadata['lines_in_step']:max_step*metadata['lines_in_step']]

    # get the data from each step in a more usable format
    step_data = np.reshape(all_data, (len(all_steps), lines_in_step))
    step_data = step_data[:, num_title_lines:]


    # This bit is the slowest atm and would benefit the most from optimisation
    step_data = np.apply_along_axis(splitter, 1, step_data)
    data = step_data[:, :, num_data_cols:].astype(float)

    # If there is only one column in the cols then don't create another list!
    if (len(step_data[0, 0]) + num_data_cols) == 1:
        cols = step_data[:, :, 0]
    else:
        cols = step_data[:, :, :num_data_cols]

    return XYZ_File(data, cols, timesteps)
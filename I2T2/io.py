# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_io.ipynb (unless otherwise specified).

__all__ = ['read_dicom_from_file', 'get_tag_from_loaded_dicom', 'dicom_dataframe', 'load_mat', 'load_h5']

# Cell
from fastscript import call_parse, Param, bool_arg
from scipy import ndimage

import h5py
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pydicom
import scipy.io as spio

# Cell
def read_dicom_from_file(dicom_file_path):
    """
    Reads dicom using pydicom.dcmread.
    Attributes:
        dicom_file_path (str): path to file of interest
    Returns:
        dcm (FileDataset): result from pydicom.dcmread()
    """
    try:
        return(pydicom.dcmread(dicom_file_path))
    except Exception as error:
        print(error)

# Cell
def get_tag_from_loaded_dicom(dcm, tag):
    """
    Get tag from loaded pydicom data structure.
    Attributes:
        dcm (FileDataset): result from pydicom.dcmread()
        tag (str): key of interest in the dicom (e.g. "SOPClassUID")
    Returns:
        content (str): the contant of the dicom key
    """
    try:
        content = dcm[tag].value
        return(content)
    except Exception as e:
        print(str(tag), " tag was not found! Skipping...", e)
        return None

# Cell
class dicom_dataframe:
    """
    Class for sorting, selecting and loading portions of dicom data.

    Objects of this class are pandas dataframes with at least one main column ('DS')
    that holds the results of pydicom.read() for each file read during initialization.
    Users can populate the dataframe with new columns using DICOM tags to facilitate
    subsequent filtering, sorting and data loading.
    """

    def __init__(self, path_to_dicom_dir, dicom_extension='dcm'):
        if not path_to_dicom_dir.endswith(('/')):
            path_to_dicom_dir = f"{path_to_dicom_dir}/"

        df = pd.DataFrame()
        df['filename'] = os.listdir(path_to_dicom_dir)
        df['pathname'] = path_to_dicom_dir + df['filename']

        #select only files containing the desired extension, lower or upper case
        df = df[df['pathname'].str.contains(dicom_extension.lower())]

        dicom_df = pd.DataFrame(columns=['DS'])
        dicom_df['DS'] = df['pathname'].apply(read_dicom_from_file)

        self.dataframe = dicom_df

        self.populate_dataframe(['SeriesInstanceUID',
                                'ImagePositionPatient'])

    def populate_dataframe(self, tags_list):
        """
        Populate pandas dataframe with columns of interest.
        Attributes:
            tags_list (list): list of DICOM tags of interest (e.g. ['SOPClassUID','SeriesInstanceUID'])
        Returns:
            updates self.dataframe with new columns.
        """
        for tag in tags_list:
            try:
                self.dataframe[tag] = self.dataframe['DS'].apply(lambda x: get_tag_from_loaded_dicom(x, tag))
            except Exception as error:
                print('Tag not found! Error: ', error)

    def filter_dataframe_by_column_value(self, column, value):
        """
        Filter pandas dataframe based on value of existing column.
        Attributes:
            column (str): column of interest (e.g. 'SOPClassUID')
            value (str): value used for dataframe subset selection
        Returns:
            updates self.dataframe to only hold request subset of data.
        """
        try:
            df_column = self.dataframe[column]
        except Exception as error:
            print('Could not find column in dataframe. Error: ', error)

        self.dataframe = self.dataframe[df_column == value]

    def get_pixel_data(self, sort_by_ImagePositionPatient=True):
        """
        Get pixel data from dataframe.
        Attributes:
            sort_by_ImagePositionPatient (bool)
        Returns:
            pixel_array (arr) numpy array containing pixel data
        """
        if 'SeriesInstanceUID' not in self.dataframe.columns:
            print('Warning: SeriesInstanceUID not found in dataset. Unable to check if dicom is single series.')

        elif len(self.dataframe['SeriesInstanceUID'].unique()) > 1:
            print('Warning: Multiple series found in dataframe. You might want to first select a single series with `select_by_column_and_values`.')

        self.dataframe['PixelArray'] = [x.pixel_array for x in self.dataframe['DS']]

        #sort by 1st dimension of ImagePositionPatient
        if sort_by_ImagePositionPatient:
            self.dataframe['ImagePositionPatient_0'] = self.dataframe['ImagePositionPatient'].apply(lambda x: x[0])
            self.dataframe.sort_values('ImagePositionPatient_0')

        pixel_array = np.dstack(np.asarray(self.dataframe.PixelArray))
        return(pixel_array)

# Cell
def load_mat(path_to_mat_file=None, key='img'):
    """
    Loads matlab data as a numpy array.

    Attributes:
        path_to_mat_file (str): Path to mat file containing image / segmentation
        key (str): key to load from matlab dictionary

    Returns:
        pixel_array (arr): Array of pixel data
    """

    try:
        os.path.isfile(path_to_mat_file)

    except:
        print("mat file not found")

    else:
        pixel_array = spio.loadmat(path_to_mat_file)[key]

        return pixel_array
    return None

# Cell
def load_h5(path_to_h5_file=None):
    """
    Loads h5 files into numpy array.

    Attributes:
        path_to_h5_file (str): Path h5 file for one subject

    Returns:
        h5_file_dict (dict): Dictionary of pixel data
    """

    try:
        h5_file = h5py.File(path_to_h5_file, 'r')

    except:
        print("File", str(path_to_h5_file), "not found.")
        print("Make sure file exists")

    else:
        h5_file_dict = dict()
        keys = h5_file.keys()

        for k in keys:
            h5_file_dict[k] = h5_file.get(k)

        return(h5_file_dict)
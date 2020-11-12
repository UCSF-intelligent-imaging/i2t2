# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_io.ipynb (unless otherwise specified).

__all__ = ['dicom_dataframe', 'get_plane', 'is_axial', 'is_sagittal', 'is_coronal', 'is_fat_suppressed', 'load_mat',
           'load_h5']

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
def _get_dcm_paths_from_folderpath(path_to_dicom_dir, dicom_extension='DCM'):
    """
    Returns a list of paths to dicom files within a directory.
    Attributes:
        path_to_dicom_dir (str): path to folder containing dicoms.
        dicom_extension (str): case insensitive str with dicom extension.
    Returns:
        dcm_paths_list (list): list of paths to dicom files.
    """
    if not path_to_dicom_dir.endswith(('/')):
        path_to_dicom_dir = f"{path_to_dicom_dir}/"

    filenames_list = os.listdir(path_to_dicom_dir)

    dcm_paths_list = [os.path.join(path_to_dicom_dir, name) for name in filenames_list if str.lower(dicom_extension) in str.lower(name)]

    return(dcm_paths_list)

# Cell
def _read_dicom_from_file(dicom_file_path):
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
def _get_tag_from_loaded_dicom(dcm, tag):
    """
    Get tag from loaded pydicom data structure.
    Attributes:
        dcm (FileDataset): dicom slice, result from pydicom.dcmread()
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
def _get_normal_from_dicom_slice(dcm):
    """
    Get normal vector from a dicom slice.
    Attributes:
        dcm (FileDataset): dicom slice, result from pydicom.dcmread()
    Returns:
        normal_vector (arr): numpy array with dimensions of slice's normal vector
    """

    cosines = _get_tag_from_loaded_dicom(dcm,'ImageOrientationPatient')
    cosines = [float(i) for i in cosines]

    normal = np.empty(3)
    normal[0] = cosines[1]*cosines[5] - cosines[2]*cosines[4];
    normal[1] = cosines[2]*cosines[3] - cosines[0]*cosines[5];
    normal[2] = cosines[0]*cosines[4] - cosines[1]*cosines[3];
    return(np.array(normal))

# Cell
def _get_dicom_slice_IPP_along_normal(dcm):
    """
    Get dicom slice ImagePositionPatient (IPP) in the direction of the slice's normal vector
    Attributes:
        dcm (FileDataset): dicom slice, result from pydicom.dcmread()
    Returns:
        slice_ipp (double): ImagePositionPatient value along slice's normal vector
    """

    IPP = _get_tag_from_loaded_dicom(dcm, 'ImagePositionPatient')
    IPP = [float(i) for i in IPP]
    slice_ipp = np.inner(_get_normal_from_dicom_slice(dcm), IPP)

    return(slice_ipp)

# Cell
def _get_distance_between_two_dicom_slices(dcm1, dcm2):
    """
    Get distance between two dicom slices along the normal vector
    Attributes:
        dcm1 (FileDataset): dicom slice, result from pydicom.dcmread()
        dcm2 (FileDataset): dicom slice, result from pydicom.dcmread()
    Returns:
        distance_vector (arr): numpy array with difference between center of two slices
    """

    slice_position_1 = _get_dicom_slice_IPP_along_normal(dcm1)

    slice_position_2 = _get_dicom_slice_IPP_along_normal(dcm2)

    distance = np.abs(slice_position_2 - slice_position_1)

    return(distance)

# Cell
class dicom_dataframe:
    """
    Class for sorting, selecting and loading portions of dicom data.

    Objects of this class are pandas dataframes with at least one main column ('DS')
    that holds the results of pydicom.read() for each file read during initialization.
    Users can populate the dataframe with new columns using DICOM tags to facilitate
    subsequent filtering, sorting and data loading.
    """

    def __init__(self, path_to_dicom_dir, dicom_extension='dcm', read_single_random_dcm=False):
        if not path_to_dicom_dir.endswith(('/')):
            path_to_dicom_dir = f"{path_to_dicom_dir}/"

        df = pd.DataFrame()
        list_of_paths = _get_dcm_paths_from_folderpath(path_to_dicom_dir, dicom_extension)

        if read_single_random_dcm:
            import random
            list_of_paths = random.sample(list_of_paths, 1)

        df['pathname'] = list_of_paths

        #to get the filenames just remove the path from it
        df['filename'] = df['pathname'].str.replace(path_to_dicom_dir, '')

        if df.empty:
            raise ValueError('Empty dataframe! Incorrect dicom extension?')


        dicom_df = pd.DataFrame(columns=['DS'])
        dicom_df['DS'] = df['pathname'].apply(_read_dicom_from_file)

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
                self.dataframe[tag] = self.dataframe['DS'].apply(lambda x: _get_tag_from_loaded_dicom(x, tag))
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

    def sort_dataframe_by_IPP_normal(self):
        """
        Sort dicoms dataframe by ImagePositionPatient value in the direction of the slice normal
        """
        self.dataframe['ImagePositionPatient_normal'] = self.dataframe['DS'].apply(lambda x: _get_dicom_slice_IPP_along_normal(x))
        self.dataframe = self.dataframe.sort_values('ImagePositionPatient_normal')
        self.dataframe.reset_index(drop=True)

    def get_pixel_data(self):
        """
        Get pixel data from dataframe.
        Returns:
            pixel_array (arr) numpy array containing pixel data
        """

        self.dataframe['PixelArray'] = [x.pixel_array for x in self.dataframe['DS']]

        num_slices = len(self.dataframe)
        if  num_slices > 1:
            if 'SeriesInstanceUID' not in self.dataframe.columns:
                print('Warning: SeriesInstanceUID not found in dataset. Unable to check if dicom is single series.')
            elif len(self.dataframe['SeriesInstanceUID'].unique()) > 1:
                print('Warning: Multiple series found in dataframe. You might want to first select a single series with `select_by_column_and_values`.')

            self.sort_dataframe_by_IPP_normal()

        pixel_array = np.dstack(np.asarray(self.dataframe.PixelArray))

        return(pixel_array)

# Cell
import numpy as np
def get_plane(dcm):
    """
    Returns plane for input dicom
    Attributes:
        dcm (FileDataset): dicom slice, result from pydicom.dcmread()
    Returns:
        plane (str): axial or coronal or sagittal
    """
    if hasattr(dcm, 'ImageOrientationPatient'):
        IOP = _get_tag_from_loaded_dicom(dcm, 'ImageOrientationPatient')
        IOP_round = [round(x) for x in IOP]
        plane = np.cross(IOP_round[0:3], IOP_round[3:6])
        plane = [abs(x) for x in plane]
        if plane[0] == 1:
            return "sagittal"
        elif plane[1] == 1:
            return "coronal"
        elif plane[2] == 1:
            return "axial"
        else:
            return "Oblique acquisition (hope for the best)."
    else:
        raise KeyError('ImageOrientationPatient not in dicom')

def is_axial(dcm):
    return (get_plane(dcm) == "axial")

def is_sagittal(dcm):
    return (get_plane(dcm) == "sagittal")

def is_coronal(dcm):
    return (get_plane(dcm) == "coronal")

def is_fat_suppressed(dcm):
    if hasattr(dcm, 'ScanOptions'):
        return('FS' in _get_tag_from_loaded_dicom(dcm, 'ScanOptions'))
    else:
        raise KeyError('ScanOptions not in dicom')

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
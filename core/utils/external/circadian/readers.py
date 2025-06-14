"""Defines several methods for analyzing, plotting, and exporting wearable data, including a Pandas accessor for wearable dataframes"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/05_readers.ipynb.

# %% auto 0
__all__ = ['VALID_WEARABLE_STREAMS', 'ACTIWATCH_COLUMN_RENAMING', 'WEARABLE_RESAMPLE_METHOD', 'WearableData', 'load_json',
           'load_csv', 'load_actiwatch', 'interval_fraction', 'resample_df', 'combine_wearable_dataframes']

# %% ../nbs/api/05_readers.ipynb 4
import json
import numpy as np
import pandas as pd
from typing import Dict

# %% ../nbs/api/05_readers.ipynb 6
VALID_WEARABLE_STREAMS = ['steps', 'heartrate', 'wake', 'light_estimate', 'activity']

# %% ../nbs/api/05_readers.ipynb 7
@pd.api.extensions.register_dataframe_accessor("wearable")
class WearableData:
    "pd.DataFrame accessor implementing wearable-specific methods"
    def __init__(self, pandas_obj):
        self._validate_columns(pandas_obj)
        self._obj = pandas_obj

    @staticmethod
    def _validate_columns(obj):
        if 'datetime' not in obj.columns:
            if 'start' not in obj.columns and 'end' not in obj.columns:
                raise AttributeError("DataFrame must have 'datetime' column or 'start' and 'end' columns")

        if not any([col in obj.columns for col in VALID_WEARABLE_STREAMS]):
            raise AttributeError(f"DataFrame must have at least one wearable data column from: {VALID_WEARABLE_STREAMS}.")
        
    @staticmethod
    def _validate_metadata(metadata):
        if metadata:
            if not isinstance(metadata, dict):
                raise AttributeError("Metadata must be a dictionary.")
            if not any([key in metadata.keys() for key in ['data_id', 'subject_id']]):
                raise AttributeError("Metadata must have at least one of the following keys: data_id, subject_id.")
            if not all([isinstance(value, str) for value in metadata.values()]):
                raise AttributeError("Metadata values must be strings.")
    
    @staticmethod
    def rename_columns(df, 
                       inplace: bool = False
                       ):
        "Standardize column names by making them lowercase and replacing spaces with underscores"
        columns = [col.lower().replace(' ', '_') for col in df.columns]
        if inplace:
            df.columns = columns
        else:
            new_df = df.copy()
            new_df.columns = columns
            return new_df

    def is_valid(self):
        self._validate_columns(self._obj)
        self._validate_metadata(self._obj.attrs)
        return True

    def add_metadata(self,
                     metadata: Dict[str, str], # metadata containing data_id, subject_id, or other_info
                     inplace: bool = False, # whether to return a new dataframe or modify the current one
                     ):
        self._validate_metadata(metadata)
        if inplace:
            for key, value in metadata.items():
                self._obj.attrs[key] = value
        else:
            obj = self._obj.copy()
            for key, value in metadata.items():
                obj.attrs[key] = value
            return obj

# %% ../nbs/api/05_readers.ipynb 9
def load_json(filepath: str, # path to file
              metadata: Dict[str, str] = None, # metadata containing data_id, subject_id, or other_info
              ) -> Dict[str, pd.DataFrame]: # dictionary of wearable dataframes, one key:value pair per wearable data stream
    "Create a dataframe from a json containing a single or multiple streams of wearable data"
    # validate inputs
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    # load json
    jdict = json.load(open(filepath, 'r'))
    # check that it contains valid keys
    if not np.all([key in VALID_WEARABLE_STREAMS for key in jdict.keys()]):
        raise AttributeError("Invalid keys in JSON file. At least one key must be steps, heartrate, wake, light_estimate, or activity.")
    # create a df for each wearable stream
    df_dict = {}
    for key in jdict.keys():
        if key in VALID_WEARABLE_STREAMS:
            df_dict[key] = pd.DataFrame.from_dict(jdict[key])
        else:
            print(f"Excluded key: {key} because it's not a valid wearable stream column name.")
    for key in df_dict.keys():
        df = df_dict[key]
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        elif 'start' in df.columns and 'end' in df.columns:
            df['start'] = pd.to_datetime(df['start'], unit='s')
            df['end'] = pd.to_datetime(df['end'], unit='s')
        if metadata is not None:
            df.wearable.add_metadata(metadata, inplace=True)
        else:
            df.wearable.add_metadata({'data_id': 'unknown', 'subject_id': 'unknown'}, inplace=True)
        df_dict[key] = df
    return df_dict

# %% ../nbs/api/05_readers.ipynb 10
def load_csv(filepath: str, # full path to csv file to be loaded
             metadata: Dict[str, str] = None, # metadata containing data_id, subject_id, or other_info
             timestamp_col: str = None, # name of the column to be used as timestamp. If None, it is assumed that a `datetime` column exists
             *args, # arguments to pass to pd.read_csv
             **kwargs, # keyword arguments to pass to pd.read_csv
             ):
    "Create a dataframe from a csv containing wearable data"
    # validate inputs
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if not isinstance(timestamp_col, str) and timestamp_col is not None:
        raise AttributeError("Timestamp column must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    # load csv
    df = pd.read_csv(filepath, *args, **kwargs)
    # create datetime column
    if timestamp_col is not None:
        df['datetime'] = pd.to_datetime(df[timestamp_col], unit='s')
    if timestamp_col is None:
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'start' in df.columns and 'end' in df.columns:
            df['start'] = pd.to_datetime(df['start'])
            df['end'] = pd.to_datetime(df['end'])
        if 'datetime' not in df.columns and 'start' not in df.columns and 'end' not in df.columns:
            raise AttributeError("CSV file must have a column named 'datetime' or 'start' and 'end'")
    # add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({'data_id': 'unknown', 'subject_id': 'unknown'}, inplace=True)
    return df

# %% ../nbs/api/05_readers.ipynb 11
ACTIWATCH_COLUMN_RENAMING = {
    'White Light': 'light_estimate',
    'Sleep/Wake': 'wake',
    'Activity': 'activity',
} 

# %% ../nbs/api/05_readers.ipynb 12
def load_actiwatch(filepath: str, # full path to csv file to be loaded
                   metadata: Dict[str, str] = None, # metadata containing data_id, subject_id, or other_info
                   *args, # arguments to pass to pd.read_csv
                   **kwargs, # keyword arguments to pass to pd.read_csv
                   ) -> pd.DataFrame: # dataframe with the wearable data
    "Create a dataframe from an actiwatch csv file"
    # validate inputs
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    # load csv
    df = pd.read_csv(filepath, *args, **kwargs)
    df['datetime'] = pd.to_datetime(df['Date']+" "+df['Time'])
    # drop unnecessary columns
    df.drop(columns=['Date', 'Time'], inplace=True)
    # rename columns
    df.rename(columns=ACTIWATCH_COLUMN_RENAMING, inplace=True)
    # add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({'data_id': 'unknown', 'subject_id': 'unknown'}, inplace=True)
    return df

# %% ../nbs/api/05_readers.ipynb 14
def interval_fraction(
        starts: pd.Series, # start datetimes of intervals
        stops: pd.Series, # stop datetimes of intervals
        ref_start: pd.Timestamp, # start datetime of reference interval
        ref_stop: pd.Timestamp # stop datetime of reference interval
        ):
        "Calculate the fraction of each interval contained in the reference interval."
        max_starts = starts.apply(lambda x: max(x, ref_start))
        min_ends = stops.apply(lambda x: min(x, ref_stop))
        contained_intervals = (min_ends - max_starts).apply(lambda x: x.seconds)
        full_intervals = (stops - starts).apply(lambda x: x.seconds)
        return contained_intervals / full_intervals

# %% ../nbs/api/05_readers.ipynb 15
def resample_df(df: pd.DataFrame, # dataframe to be resampled
                name: str, # name of the wearable data to resample (one of steps, heartrate, wake, light_estimate, or activity)
                freq: str, # frequency to resample to. String must be a valid pandas frequency string (e.g. '1min', '5min', '1H', '1D'). See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
                agg_method: str, # aggregation method to use when resampling
                initial_datetime: pd.Timestamp = None, # initial datetime to use when resampling. If None, the minimum datetime in the dataframe is used
                final_datetime: pd.Timestamp = None, # final datetime to use when resampling. If None, the maximum datetime in the dataframe is used
                ) -> pd.DataFrame: # resampled dataframe
    "Resample a wearable dataframe. If data is specified in intervals, returns the density of the quantity per minute."
    # validate inputs
    if not df.wearable.is_valid():
        raise AttributeError("Dataframe must be a valid wearable dataframe.")
    if not isinstance(df, pd.DataFrame):
        raise AttributeError("Dataframe must be a pandas dataframe.")
    if not isinstance(freq, str):
        raise AttributeError("Frequency must be a string.")
    if name is not None and name not in VALID_WEARABLE_STREAMS:
        raise AttributeError(f"Name must be one of: {VALID_WEARABLE_STREAMS}.")
    if name not in df.columns:
        raise AttributeError(f"Name must be one of: {df.columns}.")
    if agg_method not in ['sum', 'mean', 'max', 'min']:
        raise AttributeError("Aggregation method must be one of: sum, mean, max, min.")
    if initial_datetime is not None and not isinstance(initial_datetime, pd.Timestamp):
        raise AttributeError("Initial datetime must be a pandas timestamp.")
    if final_datetime is not None and not isinstance(final_datetime, pd.Timestamp):
        raise AttributeError("Final datetime must be a pandas timestamp.")
    # resample
    values = df[name]
    if 'start' in df.columns and 'end' in df.columns:
        # data is specified in intervals
        starts = df.start
        stops = df.end
        if initial_datetime is None:
            initial_datetime = starts.min()
        if final_datetime is None:
            final_datetime = stops.max()
        new_datetime = pd.date_range(initial_datetime, final_datetime, freq=freq)
        new_values = np.zeros(len(new_datetime))
        for idx, datetime in enumerate(new_datetime):
            next_datetime = datetime + pd.to_timedelta(freq)
            mask = (starts <= next_datetime) & (stops > datetime)
            if len(values[mask]) > 0:
                # calculate the fraction of each interval contained in the resampled interval
                value_fraction = interval_fraction(starts[mask], stops[mask], datetime, next_datetime)
                new_values[idx] = (values[mask] * value_fraction).agg(agg_method)
    else:
        # data is specified per datetime
        data_datetimes = df.datetime
        if initial_datetime is None:
            initial_datetime = data_datetimes.min()
        if final_datetime is None:
            final_datetime = data_datetimes.max()
        new_datetime = pd.date_range(initial_datetime, final_datetime, freq=freq)
        new_values = np.zeros(len(new_datetime))
        for idx, datetime in enumerate(new_datetime):
            next_datetime = datetime + pd.to_timedelta(freq)
            mask = (data_datetimes <= next_datetime) & (data_datetimes >= datetime)
            if len(values[mask]) > 0:
                new_values[idx] = values[mask].agg(agg_method)

    return pd.DataFrame({'datetime': new_datetime, name: new_values})

# %% ../nbs/api/05_readers.ipynb 17
WEARABLE_RESAMPLE_METHOD = {
    'steps': 'sum',
    'wake': 'max',
    'heartrate': 'mean',
    'light_estimate': 'mean',
    'activity': 'mean',
}

# %% ../nbs/api/05_readers.ipynb 18
def combine_wearable_dataframes(df_dict: Dict[str, pd.DataFrame], # dictionary of wearable dataframes 
                                resample_freq: str, # resampling frequency (e.g. '10min' for 10 minutes, see Pandas Offset aliases: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases)
                                metadata: Dict[str, str] = None, # metadata for the combined dataframe
                                ) -> pd.DataFrame: # combined wearable dataframe
    "Combine a dictionary of wearable dataframes into a single dataframe with resampling"
    df_list = []
    # find common initial and final datetimes
    initial_datetimes = []
    final_datetimes = []
    for name in df_dict.keys():
        df = df_dict[name]
        df.wearable.is_valid()
        if 'start' in df.columns:
            initial_datetimes.append(df.start.min())
            final_datetimes.append(df.end.max())
        else:
            initial_datetimes.append(df.datetime.min())
            final_datetimes.append(df.datetime.max())
    initial_datetime = min(initial_datetimes)
    final_datetime = max(final_datetimes)
    # resample each df
    for name in df_dict.keys():
        df = df_dict[name]
        new_df = resample_df(df, name, resample_freq, 
                             WEARABLE_RESAMPLE_METHOD[name],
                             initial_datetime=initial_datetime,
                             final_datetime=final_datetime)
        df_list.append(new_df)
    # merge all dfs by datetime
    df = df_list[0]
    for i in range(1, len(df_list)):
        df = df.merge(df_list[i], on='datetime', how='outer')
    # sort by datetime
    df.sort_values(by='datetime', inplace=True)
    # add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({'data_id': 'combined_dataframe'}, inplace=True)
    return df
"""Defines metrics to quantify circadian disruption"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/04_metrics.ipynb.

# %% auto 0
__all__ = ['esri']

# %% ../nbs/api/04_metrics.ipynb 4
import warnings
import numpy as np
from typing import List
from .models import Hannay19
from .lights import LightSchedule

# %% ../nbs/api/04_metrics.ipynb 5
def esri(time: np.ndarray, # time in hours to use for the simulation 
         light_schedule: np.ndarray, # light schedule in lux 
         analysis_days: int=4, # number of days used to calculate ESRI
         esri_dt: float=1.0, # time resolution of the ESRI calculation in hours
         initial_amplitude: float=0.1, # initial amplitude for the simulation. This is the ESRI value for constant darkness
         phase_at_midnight: float=1.65238233, # phase at midnight. Default value corresponds to a 8 hour darkness and 16 hour light schedule with wake at 8 am.
         ) -> List: # list with ESRI timepoints and ESRI values. Negative ESRI values are turned into NaNs
        "Calculate the ESRI metric for a given light schedule. Follows the implementation from Moreno et al. 2023 'Validation of the Entrainment Signal Regularity Index and associations with children's changes in BMI'"
        # validate inputs
        if not isinstance(time, np.ndarray):
            raise TypeError(f'time must be a numpy array, not {type(time)}')
        if not isinstance(light_schedule, np.ndarray):
            raise TypeError(f'light_schedule must be a numpy array, not {type(light_schedule)}')
        if len(time) != len(light_schedule):
            raise ValueError(f'time and light_schedule must be the same length')
        if not np.all(np.isclose(np.diff(time), np.diff(time)[0])):
            raise ValueError(f'time must have a fixed time resolution (time between timepoints must be constant)')
        if not isinstance(analysis_days, int):
            raise TypeError(f'analysis_days must be an integer, not {type(analysis_days)}')
        if analysis_days < 1:
            raise ValueError(f'analysis_days must be greater than 0')
        if not isinstance(esri_dt, (int, float)):
            raise TypeError(f'esri_dt must be a float or an int, not {type(esri_dt)}')
        if esri_dt <= 0:
            raise ValueError(f'esri_dt must be greater than 0')
        if not isinstance(initial_amplitude, (int, float)):
            raise TypeError(f'initial_amplitude must be a float or an int, not {type(initial_amplitude)}')
        if initial_amplitude < 0:
            raise ValueError(f'initial_amplitude must be non-negative')
        # calculate ESRI 
        model = Hannay19(params={'K': 0.0, 'gamma': 0.0}) # with these parameters, amplitude is constant in the absence of light
        simulation_dt = np.diff(time)[0]
        esri_time = np.arange(time[0], time[-1] - analysis_days*24, esri_dt)
        esri_array = np.zeros_like(esri_time)
        for idx, t in enumerate(esri_time):
            initial_phase = phase_at_midnight + np.mod(t, 24.0) * np.pi / 12 # assumes regular schedule with wake at 8 am
            initial_condition = np.array([initial_amplitude, initial_phase, 0.0])
            simulation_time = np.arange(t, t + analysis_days*24, simulation_dt)
            simulation_light = np.interp(simulation_time, time, light_schedule)
            trajectory = model(simulation_time, initial_condition, simulation_light)
            esri_value = trajectory.states[-1, 0] # model amplitude at the end of the simulation
            esri_array[idx] = esri_value
        # clean up any negative values
        esri_array[esri_array < 0] = np.nan
        # if there's any NaNs, throw a warning thay probably dt was too small
        if np.any(np.isnan(esri_array)):
            warnings.warn(f'ESRI calculation failed for certain timepoints (NaN ESRI values). Try decreasing the time resolution of the `time` and `light_schedule` arrays.')
        return esri_time, esri_array
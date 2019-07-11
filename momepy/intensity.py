#!/usr/bin/env python
# -*- coding: utf-8 -*-

# intensity.py
# definitons of intensity characters

from tqdm import tqdm  # progress bar
import pandas as pd
import numpy as np
import collections


def covered_area_ratio(left, right, left_areas, right_areas, unique_id):
    """
    Calculate covered area ratio of objects.

    .. math::
        \\textit{covering object area} \\over \\textit{covered object area}

    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing objects being covered (e.g. land unit)
    right : GeoDataFrame
        GeoDataFrame with covering objects (e.g. building)
    left_areas : str
        name of the column of left gdf where is stored area value
    right_areas : str
        name of the column of right gdf where is stored area value
    unique_id : str
        name of the column with unique id shared amongst left and right gdfs.
        If there is none, it could be generated by unique_id().

    Returns
    -------
    Series
        Series containing resulting values.

    References
    ---------

    """
    print('Calculating covered area ratio...')

    print('Merging DataFrames...')
    look_for = right[[unique_id, right_areas]]  # keeping only necessary columns
    look_for.rename(index=str, columns={right_areas: 'lf_area'}, inplace=True)
    objects_merged = left.merge(look_for, on=unique_id)  # merging dataframes together

    print('Calculating CAR...')

    # define empty list for results
    results_list = []

    # fill new column with the value of area, iterating over rows one by one
    for index, row in tqdm(objects_merged.iterrows(), total=objects_merged.shape[0]):
        results_list.append(row['lf_area'] / row[left_areas])

    series = pd.Series(results_list)

    print('Covered area ratio calculated.')
    return series


def floor_area_ratio(left, right, left_areas, right_areas, unique_id):
    """
    Calculate floor area ratio of objects.

    .. math::
        \\textit{covering object floor area} \\over \\textit{covered object area}

    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing objects being covered (e.g. land unit)
    right : GeoDataFrame
        GeoDataFrame with covering objects (e.g. building)
    left_areas : str
        name of the column of left gdf where is stored area value
    right_areas : str
        name of the column of right gdf where is stored floor area value
    unique_id : str
        name of the column with unique id shared amongst left and right gdfs.
        If there is none, it could be generated by unique_id().

    Returns
    -------
    Series
        Series containing resulting values.

    References
    ---------

    """
    print('Calculating floor area ratio...')

    print('Merging DataFrames...')
    look_for = right[[unique_id, right_areas]]  # keeping only necessary columns
    look_for.rename(index=str, columns={right_areas: 'lf_area'}, inplace=True)
    objects_merged = left.merge(look_for, on=unique_id)  # merging dataframes together

    print('Calculating FAR...')

    # define empty list for results
    results_list = []

    # fill new column with the value of area, iterating over rows one by one
    for index, row in tqdm(objects_merged.iterrows(), total=objects_merged.shape[0]):
        results_list.append(row['lf_area'] / row[left_areas])

    series = pd.Series(results_list)

    print('Floor area ratio calculated.')
    return series


def elements_count(left, right, left_id, right_id, weighted=False):
    """
    Calculate the number of elements within aggregated structure.

    Aggregated structure can be typically block, street segment or street node (their snapepd objects). Right gdf has to have
    unique id of aggregated structure assigned before hand (e.g. using :py:func:`momepy.get_network_id`).
    If weighted=True, number of elements will be divided by the area of lenght (based on geometry type) of aggregated
    element, to return relative value.

    .. math::
        \\sum_{i \\in aggr} (n_i);\\space \\frac{\\sum_{i \\in aggr} (n_i)}{area_{aggr}}

    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing aggregation to analyse
    right : GeoDataFrame
        GeoDataFrame containing objects to analyse
    left_id : str
        name of the column where is stored unique ID in aggr
    right_id : str
        name of the column where is stored unique ID of aggregation in elements gdf
    weighted : bool (default False)
        if weighted=True, count will be divided by the area or length

    Returns
    -------
    Series
        Series containing resulting values.

    References
    ---------
    Hermosilla T, Ruiz LA, Recio JA, et al. (2012) Assessing contextual descriptive features
    for plot-based classification of urban areas. Landscape and Urban Planning, Elsevier B.V.
    106(1): 124–137.
    Feliciotti A (2018) RESILIENCE AND URBAN DESIGN:A SYSTEMS APPROACH TO THE
    STUDY OF RESILIENCE IN URBAN FORM. LEARNING FROM THE CASE OF GORBALS. Glasgow.
    """
    count = collections.Counter(right[right_id])
    df = pd.DataFrame.from_dict(count, orient='index', columns=['mm_count'])
    joined = left.join(df['mm_count'], on=left_id)
    joined['mm_count'][np.isnan(joined['mm_count'])] = 0

    if weighted:
        if left.geometry[0].type in ['Polygon', 'MultiPolygon']:
            joined['mm_count'] = joined['mm_count'] / left.geometry.area
        elif left.geometry[0].type in ['LineString', 'MultiLineString']:
            joined['mm_count'] = joined['mm_count'] / left.geometry.length
        else:
            raise TypeError('Geometry type does not support weighting.')

    return joined['mm_count']


def courtyards(gdf, block_id, spatial_weights=None):
    """
    Calculate the number of courtyards within the joined structure.

    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame containing objects to analyse
    block_id : str
        name of the column where is stored block ID
    spatial_weights : libpysal.weights, optional
        spatial weights matrix - If None, Queen contiguity matrix will be calculated
        based on objects. It is to denote adjacent buildings (note: based on index).

    Returns
    -------
    Series
        Series containing resulting values.

    Notes
    -----
    Script is not optimised at all, so it is currently extremely slow.
    """
    # define empty list for results
    results_list = []

    print('Calculating courtyards...')

    # if weights matrix is not passed, generate it from objects
    if spatial_weights is None:
        print('Calculating spatial weights...')
        from libpysal.weights import Queen
        spatial_weights = Queen.from_dataframe(gdf, silence_warnings=True)
        print('Spatial weights ready...')

    # dict to store nr of courtyards for each uID
    courtyards = {}

    for index, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
        # if the id is already present in courtyards, continue (avoid repetition)
        if index in courtyards:
            continue
        else:
            to_join = [index]  # list of indices which should be joined together
            neighbours = []  # list of neighbours
            weights = spatial_weights.neighbors[index]  # neighbours from spatial weights
            for w in weights:
                neighbours.append(w)  # make a list from weigths

            for n in neighbours:
                while n not in to_join:  # until there is some neighbour which is not in to_join
                    to_join.append(n)
                    weights = spatial_weights.neighbors[n]
                    for w in weights:
                        neighbours.append(w)  # extend neighbours by neighbours of neighbours :)
            joined = gdf.iloc[to_join]
            dissolved = joined.geometry.buffer(0.01).unary_union  # buffer to avoid multipolygons where buildings touch by corners only
            try:
                interiors = len(list(dissolved.interiors))
            except(ValueError):
                print('Something happened.')
            for b in to_join:
                courtyards[b] = interiors  # fill dict with values
    # copy values from dict to gdf
    for index, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
        results_list.append(courtyards[index])

    series = pd.Series(results_list)
    print('Courtyards calculated.')
    return series


def blocks_count(gdf, block_id, spatial_weights, unique_id):
    """
    Calculates the weighted number of blocks

    Number of blocks within `k` topological steps defined in spatial_weights weighted by the analysed area.

    .. math::


    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame containing morphological tessellation
    block_id : str, list, np.array, pd.Series
        the name of the objects dataframe column, np.array, or pd.Series where is stored block ID.
    spatial_weights : libpysal.weights
        spatial weights matrix
    unique_id : str
        name of the column with unique id used as spatial_weights index.


    Returns
    -------
    Series
        Series containing resulting values.

    References
    ----------
    Jacob

    Examples
    --------

    Notes
    -----
    Blocks count or blocks density?

    """
    # define empty list for results
    results_list = []
    gdf = gdf.copy()
    if not isinstance(block_id, str):
        block_id['mm_bid'] = block_id
        block_id = 'mm_bid'

    print('Calculating blocks...')

    for index, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
        neighbours = spatial_weights.neighbors[row[unique_id]]
        if neighbours:
            neighbours.append(row[unique_id])
        else:
            neighbours = row[unique_id]
        vicinity = gdf.loc[gdf[unique_id].isin(neighbours)]

        results_list.append(len(set(list(vicinity[block_id]))) / sum(vicinity.geometry.area))

    series = pd.Series(results_list)

    print('Blocks calculated.')
    return series


def reached(left, right, unique_id, spatial_weights=None, mode='count', values=None):
    """
    Calculates the number of objects reached within topological steps on street network

    Number of elements within topological steps defined in spatial_weights. If
    spatial_weights are None, it will assume topological distance 0 (element itself).
    If mode='area', returns sum of areas of reached elements. Requires unique_id
    of streets assigned beforehand (e.g. using :py:func:`momepy.get_network_id`).

    .. math::


    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing streets (either segments or nodes)
    right : GeoDataFrame
        GeoDataFrame containing elements to be counted
    unique_id : str, list, np.array, pd.Series (default None)
        the name of the right dataframe column, np.array, or pd.Series where is
        stored ID of streets (segments or nodes).
    spatial_weights : libpysal.weights (default None)
        spatial weights matrix
    mode : str (default 'count')
        mode of calculation. If `'count'` function will return the count of reached elements.
        If `'sum'`, it will return sum of `'values'`. If `'mean'` it will return mean value
        of `'values'`. If `'std'` it will return standard deviation
        of `'values'`. If `'values'` not set it will use of areas
        of reached elements.
    values : str (default None)
        the name of the objects dataframe column with values used for calculations

    Returns
    -------
    Series
        Series containing resulting values.

    References
    ----------

    Examples
    --------

    """
    # define empty list for results
    results_list = []

    print('Calculating reached {}...'.format(mode))

    if not isinstance(unique_id, str):
        right = right.copy()
        right['mm_id'] = unique_id
        unique_id = 'mm_id'

    if mode == 'count':
        count = collections.Counter(right[unique_id])

    # iterating over rows one by one
    for index, row in tqdm(left.iterrows(), total=left.shape[0]):
        if spatial_weights is None:
            ids = [row.nID]
        else:
            neighbours = spatial_weights.neighbors[index]
            neighbours.append(index)
            ids = left.iloc[neighbours].nID
        if mode == 'count':
            counts = []
            for nid in ids:
                counts.append(count[nid])
            results_list.append(sum(counts))
        elif mode == 'sum':
            if values:
                results_list.append(sum(right.loc[right[unique_id].isin(ids)][values]))
            else:
                results_list.append(sum(right.loc[right[unique_id].isin(ids)].geometry.area))
        elif mode == 'mean':
            if values:
                results_list.append(np.nanmean(right.loc[right[unique_id].isin(ids)][values]))
            else:
                results_list.append(np.nanmean(right.loc[right[unique_id].isin(ids)].geometry.area))
        elif mode == 'std':
            if values:
                results_list.append(np.nanstd(right.loc[right[unique_id].isin(ids)][values]))
            else:
                results_list.append(np.nanstd(right.loc[right[unique_id].isin(ids)].geometry.area))

    series = pd.Series(results_list)

    print('Reached {} calculated.'.format(mode))
    return series


def node_density(left, right, spatial_weights, weighted=False, node_degree=None, node_start='node_start', node_end='node_end'):
    """
    Calculate the density of nodes within topological steps on street network defined in spatial_weights.

    Calculated as number of nodes within k steps / cummulative length of street network within k steps.
    node_start and node_end is standard output of :py:func:`momepy.nx_to_gdf` and is compulsory.

    .. math::


    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing nodes of street network
    right : GeoDataFrame
        GeoDataFrame containing edges of street network
    spatial_weights : libpysal.weights, optional
        spatial weights matrix capturing relationship between nodes within set topological distance
    weighted : bool
        if True density will take into account node degree as k-1
    node_degree : str
        name of the column of left gdf containing node degree
    node_start : str
        name of the column of right gdf containing id of starting node
    node_end : str
        name of the column of right gdf containing id of ending node

    Returns
    -------
    Series
        Series containing resulting values.

    References
    ---------
    Jacob

    Notes
    -----

    """
    # define empty list for results
    results_list = []

    print('Calculating node density...')

    # iterating over rows one by one
    for index, row in tqdm(left.iterrows(), total=left.shape[0]):

        neighbours = list(spatial_weights.neighbors[index])
        neighbours.append(index)
        if weighted:
            neighbour_nodes = left.iloc[neighbours]
            number_nodes = sum(neighbour_nodes[node_degree] - 1)
        else:
            number_nodes = len(neighbours)

        edg = right.loc[right['node_start'].isin(neighbours)].loc[right['node_end'].isin(neighbours)]
        length = sum(edg.geometry.length)

        if length > 0:
            results_list.append(number_nodes / length)
        else:
            results_list.append(0)

    series = pd.Series(results_list)
    print('Node density calculated.')
    return series

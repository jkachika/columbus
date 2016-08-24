# Columbus - A Cloud based Scientific Workflow Engine for Multi-Dimensional Geospatial Datasets

Columbus is a workflow engine written in python 2.7 at [Colorado State University](http://www.cs.colostate.edu/~sangmi/). It supports execution of workflows that can be represented as a [Directed Acyclic Graph(DAG)](https://en.wikipedia.org/wiki/Directed_acyclic_graph). The fundamental elements of the engine include components, workflows and combiners. A workflow is represented as a directed acyclic graph with nodes being components or combiners and edges represent the data flow.

### Components
Basic building block of the engine. It can optionally contain a script(python) to process the incoming data and can specify one or more components and combiners as its parents. Data from the parents flow as input into the component and the processed data flows out of the component. If there is no processing involved in a component, the input data itself flows out as output. A component can be a root in which case it does not have any parents and recieves the input data from the data source choosen for the workflow at runtime. The input type to a root component is always a CSV List.

### Workflows
The only executable element of the engine. A workflow allows you to choose one component as its end point from which the DAG is built. The output of the workflow is the output of the end component.

### Combiners
Combiners take a workflow as its input and combines the output of all the instances of that workflow. It does not have any parents and can optionally contain a script to process the combined data. When no processing is involved, the input data flows out as output. The input type to a combiner is always a Generic List.

### Output Types
Columbus supports the following output types - CSV List, Feature, Feature Collection, Multi Collection and Generic List. All output data is transferred as is to subsequent elements in the workflow.

**CSV List**<br>
Data is represented a list of python dictionaries.
```python
[{'car_speed': 10.54, 'ch4': 3.56, 'locality': 'Fort Collins'}, 
 {'car_speed': 11.10, 'ch4': 6.5, 'locality': 'Denver'}]
```

**Feature**<br>
Data is represented as geojson for Feature and must be an instance of [geojson.Feature](https://pypi.python.org/pypi/geojson/#feature). "properties" must be a simple dictionary with key as string and value as any of the primitive types however a Feature can include any picklable value as part of its dictionary apart from "geometry", "properties" and "type".
```python
>>> from geojson import Feature, Point

>>> my_point = Point((-3.68, 40.41))

>>> Feature(geometry=my_point)  # doctest: +ELLIPSIS
{"geometry": {"coordinates": [-3.68..., 40.4...], "type": "Point"}, "properties": {}, "type": "Feature"}
```

**Feature Collection**<br>
Data is represented as geojson for FeatureCollection and must be an instance of [geojson.FeatureCollection](https://pypi.python.org/pypi/geojson/#featurecollection). Must contain "columns" dictionary property as part of its dictionary and it should have the property names of the features in the FeatureCollection as its keys and the data type of those properties as values. A FeatureCollection can include any picklable value as part of its dictionary apart from "features", "columns" and "type".
```python
>>> from geojson import Feature, Point, FeatureCollection

>>> my_feature = Feature(geometry=Point((1.6432, -19.123)))
>>> my_feature["properties"]["temperature"] = 32.5
>>> my_other_feature = Feature(geometry=Point((-80.234, -22.532)))
>>> my_other_feature["properties"]["temperature"] = 20.7

>>> myftc = FeatureCollection([my_feature, my_other_feature])  # doctest: +ELLIPSIS
>>> myftc["columns"] = {"temperature" : "FLOAT"}
>>> print myftc
{"features": [{"geometry": {"coordinates": [1.643..., -19.12...], "type": "Point"}, 
               "properties": {"temperature": 32.5}, 
               "type": "Feature"
              }, 
              {"geometry": {"coordinates": [-80.23..., -22.53...], "type": "Point"}, 
               "properties": {"temperature": 20.7}, 
               "type": "Feature"
              }],
  "columns": {"temperature" : "FLOAT"},
  "type": "FeatureCollection"
}
```

**Multi Collection**<br>
Data is represented as a python List of [geojson.FeatureCollection](https://pypi.python.org/pypi/geojson/#featurecollection)s

**Generic List**<br>
Data is represented as a python list of any pickable python objects

### Script Usage
Scripts should make use of the internal variables `__input__` to get the input data and assign the output to `__output__` to make the data available to its dependents.
  - Reading data for a root component
    ```python
    csv_list = __input__
    ```
    
  - Reading data for a non-root component having `component-1` and `combiner-1` as its parents. `component-1` and `combiner-1` are id values of the parent component and combiner respectively
  ```python
  parent1 = __input__["component-1"]
  parent2 = __input__["combiner-1"]
  ```
  
  - Reading data for a combiner.
  ```python
  generic_list = __input__
  ```
  
  - To write data, build a structure of the chosen output type and assign it to `__output__`
  ```python
  __output__ = csv_list
  ```
  
  - Components and Combiners can be visualized if the output type is either a Feature Collection or Multi Collection. Enabling visualization on these elements will create a Google Fusion Table for the output produced by these elements and share with the interested parties mentioned in the component/combiner screen. To get the fusion table key in components whose parents are visualizers. For multi collections, a single string will have all fusion table keys separated by comma. In the following example `combiner-1` is a visualizer that produces multi collection output and `component-1` is also a visualizer that produces a feature collection as its ouput.
  ```python
  >>> component_ftkey = __input__["ftkey"]["component-1"]
  >>> combiner_ftkey = __input__["ftkey"]["combiner-1"]
  >>> print component_ftkey
  10tSob7imDONyigihnAamYK7kmidDz2l6H5b1qVSf
  >>> print combiner_ftkey
  1oMf16v9Iw4lmoOLKmjRB5hnZIXVVcWfK_rGHrtC7,1QsFzkZJtLkBeF0NkN-piGjdXl_JEnxnCk_-LAgSK
  ```
  
  - obtaining Google Earth Engine to do GIS computations
  ```python
  from pyedf.security import CredentialManager
  ee = CredentialManager.get_earth_engine()
  ```
  
  - obtaining GeoJSON from earth engine FeatureCollection
  ```python
  from pyedf.gee import get_geojson
  ftc = ee.FeatureCollection('ft:<some fusion table id>')
  ftc_geojson = get_geojson(ftc)
  ```
  
  - Using Fusion Table with Google Earth Engine
  ```python
  ftkey = __input__['ftkey']['component-1'] 
  # Loading data from fusion table
  ftc = ee.FeatureCollection('ft:' + str(ftkey))
  ```
  
  - Sending an email
  ```python
  from pyedf.email import send_mail
  send_email(['abc@xyz.com', 'def@pqr.com'], 'Subject of the Message', 
             'Hi There! This is a plain text message body', 
             '<b>Hi There!</b><br/><p>This is a HTML message body</p>') 
  ```
  
### Limitations
Columbus supports only Google Bigquery as the data source for root components at this point. 

### Installation
You need to obtain a service account json file from Google Cloud Console that has access to Earth-Engine, Google Drive, Fusion Tables and Google Bigquery and place that file under a folder named secured in the directory structure shown under Deployment section of [deployment](https://github.com/jkachika/columbus/blob/master/DEPLOYMENT.md) document. Change the following properties in columbus/prod_settings to have the correct service account file name. Note that fusion tables and google drive should use the same service account. Also consider changing other settings in the prod_settings file.
```python
# service account credentials from Google dev console for Google Earth Engine
EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Bigquery
BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
# service account credentials from Google dev console for Google Cloud Storage
CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Fusion Tables and Google Drive
FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
```

### Deployment
Refer to [deployment](https://github.com/jkachika/columbus/blob/master/DEPLOYMENT.md) document to deploy the application to a google compute engine instance running Debian (jessie).


  

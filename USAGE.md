# Columbus Application Usage

This is the place to find how to make use of Columbus from creating components to running the workflows. If you're looking for application deployment or understanding what Columbus can do or how to make use of the data flowing in and out of Columbus in your components, please refer to the [README](https://github.com/jkachika/columbus/blob/master/README.md) or [DEPLOYMENT](https://github.com/jkachika/columbus/blob/master/DEPLOYMENT.md) documents.

## Workspace
Workspace is the place to define all your elements viz. Components, Workflows, Combiners, Constraints, and Polygons. Schedules are reserved for future purpose to associate with Auto-running Workflows.

#### Components
Components are of two types - Root Components and Non-Root Components. A root component does not have to specify it's parents but the non-root components do. A component can have another component or a combiner as it's parent.

1. **Root Component**     
Use the instructions in the below image to create a Root component.     
![root-component-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/root-component-create.png)<br/><br/>
A successfully created root component will look something like this:
![root-component-success](https://github.com/jkachika/columbus/blob/master/docs/screenshots/root-component-success.png)<br/><br/>

2. **Non-root Component**    
For a non-root component, you have to specify the parents. You can choose any number of parents from the given drop-down and you can choose both Components and Combiners as the parents.
![nonroot-component-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/nonroot-component-create.png)<br/><br/>
> Note that you can neither change a root component to non-root component or the parents of a non-root component after it's creation.

  A successfully created non-root component will look something like this:
![nonroot-component-success](https://github.com/jkachika/columbus/blob/master/docs/screenshots/nonroot-component-success.png)<br/><br/>

3. **Visualizing Components**    
If you want to visualize the output of a component on a Google map, you can do so by enabling the visualize option on the component screen. Enabling visualization on a component creates a Google Fusion table and the space is limited to 1GB at this writing. So, please enable visualization only if you really need it.     
![component-visualize-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/component-visualize-create.png)<br/><br/>
> When you enable visualization on a component, make sure you select at least one interested party for the visualization otherwise you will not be able to access the visualization outside of Columbus.

> Only users having gmail e-mail address will appear in the Interested Parties drop-down. If chosen as an interested party, users can see the created Fusion table as part of their google drive.

  You should see something like this when you successfully create a component with visualization enabled.
![component-visualize-success](https://github.com/jkachika/columbus/blob/master/docs/screenshots/component-visualize-success.png)<br/><br/>

#### Workflows
Workflows help you to connect all the components together and run them. You should select only a single component that marks as the end of your workflow and you will see what all components and combiners would be involved with that flow to its right as shown below. Optionally, you can share workflows with other users in the system.

> If you share a workflow, other users will be able to use components and combiners in your workflow as parents for their components. Un-sharing a workflow later cannot fully revoke the access given to other users if they have dependencies on your elements.

  This is how the workflow screen looks like.
![workflow-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-create.png)<br/><br/>

#### Combiners
Combiners help you combine the output of multiple runs of a single workflow. You can optionally specify *start time* or *end time* or both to filter the workflow runs with in that time range.

> Start time and End time indicate the creation time of a workflow instance as listed on the Dashboard.

![combiner-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/combiner-create.png)<br/><br/>

#### Other Elements
Polygons help you constraint the data selection by arbitrary space. You can create your own polygons or import them from Google fusion tables.

Constraints help you apply a filter on the raw data given as input to your root components.

Schedules are reserved for future use.

![constraint-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/constraint-create.png)<br/><br/>
![constraint-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/constraint-create-2.png)<br/><br/>

#### Pseudo Targets
Components and Combiners that do not define any processing instructions are referred to as pseudo targets. They're helpful in building complex workflows and to keep the data flowing in a Workflow.

> You should make sure that the input and output types are matching when defining a Component or Combiner that acts as a Pseudo Target

> When defining Components having more than one parent as Pseudo targets, the output type must be a Blob

## Running Workflows
Workflows can be run from the home page by making appropriate data source choices for each root component of the selected workflow. Available data source choices include Google Bigquery, Google Drive, Galileo Storage System, and Workflow Combiner. There are two run-types for running a workflow ─ **for** and **for-each**, depending on the data source choice.

- **Google Bigquery** ─ Allows selecting a table and filtering the observations by specifying the filtering criteria on the columns of the selected table. Assume a table named [`nyc_yellow_taxi_trips`](http://www.nyc.gov/html/tlc/html/about/trip_record_data.shtml) having [several columns](http://www.nyc.gov/html/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf) including `trip_distance` and `rate_code_id` among others.
  * for: creates a single workflow instance and feeds the observations obtained by the specified selection criteria to the chosen root component. For instance, if the selection criteria on `nyc_yellow_taxi_trips` table says `trip_distance > 25` , then all the trips having trip distance more than 25 miles will be given as input to the root component of a single workflow instance.
  * for-each: creates one workflow instance per unique value of the chosen column. If the selection criteria on the `nyc_yellow_taxi_trips` table says `rate_code_id`, then 6 workflow instances will be created and all observations having same `rate_code_id` will be given as input to the same workflow instance.
  
- **Google Drive** ─ Allows users to choose CSV files and Google fusion tables from their Google Drive.
  * for: creates a single workflow instance for any chosen CSV file or Google fusion table
  * for-each: creates one workflow instance per CSV file or Google fusion table in a folder

- **Galileo Storage System** ─ Allows users to choose a table stored in the [Galileo Spacetime](https://github.com/jkachika/galileo-spacetime) storage system. Storing data in Galileo allows users visualize the presence of data globally and Columbus makes it possible to query the data constrained by arbitrary space or time. Galileo groups the query results based on space and time. If query involves only space, then results are grouped on time; if query involves only time, then results are grouped on space; if query involves both space and time, then results obtained do not need any grouping; and lastly if the query involves neither space nor time, then the results are grouped on both space and time.
  * for: creates a single workflow instance for all the data retrieved from Galileo
  * for-each: creates one workflow instance per group of results obtained from Galileo

- **Workflow Combiner** ─ The choice of data source if a Workflow contains only a Combiner as the root.
     
![workflow-run-1](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-1.png)<br/><br/>
![workflow-run-2](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-2.png)<br/><br/>
![workflow-run-3](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-3.png)<br/><br/>

## Dashboard
This is the place where users find all their workflows. Users can monitor the workflow execution, see the execution trace, visualize, or analyze the results.

![workflow-history](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history.png)<br/><br/> 
![workflow-history-2](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-2.png)<br/><br/> 
![workflow-history-3](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-3.png)<br/><br/> 
![workflow-history-4](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-4.png)<br/><br/> 
![workflow-history-5](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-5.png)<br/><br/> 
![workflow-history-6](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-6.png)<br/><br/> 

## Control Panel
Users setup with superuser privileges using Django's admin site will have access to the Columbus Control Panel. Administrators can use this page install or upgrade worker software selectively to the needed machines, monitor the state of each worker machine, or even record the activity of each machine. There is a high scope of improvement here but it can help with basic administrative things getting done.

> Workflows will not be slated for execution if any of the workers listed in the Control Panel is not connected to the master.

- **Start** ─ Starts the Columbus Workers on the selected machines
- **Stop** ─ Stops the Columbus Workers on the selected machines
- **Force Stop** ─ Kills the Columbus Workers on the selected machines. Use with caution because if you are running a Worker on Master node, it will result in killing the master too.
- **Record Activity** ─ Records the activity of all the Workers to the database for every second. Use with caution and only when absolutely needed.
- **Upgrade** ─ If there is a change in the software for Columbus worker and it was prevoiusly installed on the machines, use this button to upgrade the software on selected machines
- **Install** ─ Installs the Columbus Worker software on the selected machines. This will create a new virtual environment if one does not exist already
- **Install Prerequisites** ─ Installs the prerequisite software stack needed to make the Columbus Worker software run on the selected machines


![control-panel](https://github.com/jkachika/columbus/blob/master/docs/screenshots/control-panel.png)<br/><br/> 

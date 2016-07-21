# Columbus Application Usage

This is the place to find how to make use of Columbus from creating components to running the workflows. If you're looking for application deployment or understanding what Columbus can do or how to make use of the data flowing in and out of Columbus in your components, please refer to the [README](https://github.com/jkachika/columbus/blob/master/README.md) or [DEPLOYMENT](https://github.com/jkachika/columbus/blob/master/DEPLOYMENT.md) documents.

## Workspace

Workspace is the place to define all your elements viz. Components, Workflows, Combiners, and Constraints. As of this version, you can create Polygons and Schedules too, but they are reserved for future purposes and are not used by the application.

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
If you want to visualize the output of a component on a Google map, you can do so by enabling the visualize option on the component screen. Enabling visualization on a component creates a Google Fusion table and the space is limited to 1GB at this writing. So, please enable visualization only if you really need it. Also if your component makes use of Google Earth Engine code, then at least one of the parent components must be a visualizer.     
![component-visualize-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/component-visualize-create.png)<br/><br/>
> When you enable visualization on a component, make sure you select at least one interested party for the visualization otherwise you will not be able to access the visualization outside of Columbus. Also, only users having gmail e-mail address will appear in the Interested Parties drop-down. Users can see the created Fusion table as part of their google drive.

  You should see something like this when you successfully create a component with visualization enabled.
![component-visualize-success](https://github.com/jkachika/columbus/blob/master/docs/screenshots/component-visualize-success.png)<br/><br/>

#### Workflows
Workflows help you to connect all the components together and run them. You should select only a single component that marks as the end of your workflow and you will see what all components and combiners would be involved with that flow to its right as shown below. Optionally you can share workflows with the users in the system.
> If you share the workflow, other users will be able to create components and combiners depending on your elements. Even if you un-share the workflow later, you cannot fully revoke the access given to other users if they've dependencies on your elements.

  This is how the workflow screen looks like.
![workflow-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-create.png)<br/><br/>

#### Combiners
Combiners help you combine the output of multiple runs of a single workflow. You can optionally specify start or end or both to filter the workflow runs with in that time range.<br/>
![combiner-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/combiner-create.png)<br/><br/>

#### Constraints
Constraints help you apply a filter on the raw data given as input to your root components. The image below explains how can you create one.
![constraint-create](https://github.com/jkachika/columbus/blob/master/docs/screenshots/constraint-create.png)<br/><br/>


#### Dummy Elements
You can create components and combiners as dummy elements - meaning they do not do any processing or contain any code. They're helpful to build the connection to form a complex workflow. 
> You should make sure that the input and output types are matching for the dummy elements otherwise the workflow will fail.

## Running Workflows
All the workflows that you created or were shared with you will appear in Workflow dropdown on the Home page. Choose a data source - currently either Bigquery or Combiner (if the starting point of your workflow is a combiner) and select an appropriate workflow and click on the Start Flow button. With Bigquery as data source, a workflow could be started in two ways - for and for-each.

1. **for** - This run type allows you to choose some value for a particular column in the chosen table. Let's say the table name is `ftc_subset_2015` and it contains `date` as one of its column. You can choose this column from the feature dropdown and select an operator and enter a value for that column as explained in the images below.    
![workflow-run-1](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-1.png)<br/><br/>
![workflow-run-2](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-2.png)<br/><br/>
![workflow-run-3](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-3.png)<br/><br/>

2. **for each** - This run type allows you to chose a particular column in the chosen table. A workflow would be started for each unique value of this column in the chosen table. If the table contains 100k records for 4 days with 25k records for each day, then this run will create 4 workflows each dealing with 25k records.     
![workflow-run-4](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-4.png)<br/><br/>

3. **combiner** - Choose combiner as a data source if your workflow starts with a Combiner.    
![workflow-run-5](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-run-5.png)<br/><br/>

## History
This is the place where you find all your workflows. Currently this page shows only your past 50 runs. The image below explains the sections on this screen.   
![workflow-history](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history.png)<br/><br/> 
![workflow-history-2](https://github.com/jkachika/columbus/blob/master/docs/screenshots/workflow-history-2.png)<br/><br/> 


Install
-------
* Install requirements using
```
$> pip install -r requirements.txt
```
* install jupyter plotly extension :
```
$> jupyter labextension install @jupyterlab/plotly-extension 
```

Run
---

* Start Jupyter Lab 
```
$> jupyter lab
```

Produce report
--------------

First run notebook in Jupyter Notebook (not Lab !) and save widget state. Then :

```
$> jupyter nbconvert  --template=custom_template  --to html FinalResults.ipynb --output output/FinalResults.html
```

Add `--Exporter.preprocessors=[\"jupyter_utils.NotebookLinksProcessor\"]` to translate all ipynb links to html.



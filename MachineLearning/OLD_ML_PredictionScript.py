import pymysql
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from sqlalchemy import create_engine
from datetime import date

from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
from sklearn.metrics import r2_score
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Lasso, LassoLars
from sklearn.linear_model import ElasticNet
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
""" Classifiers
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
"""
from sklearn.impute import SimpleImputer
from sklearn.impute import KNNImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

import warnings
warnings.filterwarnings("ignore")


def pullData(table):
    """
    Function gets all data from input table
    """
    #Create connection 
    dbConnection = create_engine('mysql+pymysql://testUser:BorrisBulletDodger@localhost/scraperdb')

    #SQL Query
    sql = "SELECT * FROM " + table + ";"

    df = pd.read_sql(sql, con=dbConnection)

    return df

def cullData(dff):
    """
    Takes input dataframe and applies specific set of filters/slicers
    """

    #print(dff.shape)

    dff = dff[dff["wanted"] != True]
    #print(dff.shape)
    #dff = dff.dropna(axis=0, subset=["adExpiry"])
    #print(dff.shape)
    dff = dff[dff["model"] != "Other"]
    #print(dff.shape)
    dff = dff[(dff["adExpiry"] > date(2020, 1, 1)) | (dff["adExpiry"].isna())]
    dff = dff[dff["price"] > 400]
    dff = dff[dff["price"] < 100000]
    dff = dff[dff["price"].notna()]
    dff = dff[dff["kms"] < 100000]
    dff = dff[dff["kms"] > 0]
    #print(dff.shape)
    dff['registered'] = dff['registered'].map({'Y': 1.0, 'N': 0.0})
    dff['learner'] = dff['learner'].map({'Y': 1.0, 'N': 0.0})

    dff['sold'] = np.where(dff['adExpiry'].notna(), 1.0, 0.0)
    
    #print(dff["listType"].value_counts())
    

    df = dff[["bike_id", "model", "kms", "price", "year", "registered", "colour", "listType", "sold"]]
    df = df.set_index("bike_id")

    ss = df[df["sold"] == 1]
    s = ss["model"].value_counts()

    df = df[df["model"].isin(s.index[s >= 100]).values]
    #ss = df['model'].value_counts()
    #ssa = df["listType"].value_counts()
    #print(ssa.shape, "/", df.shape)

    #print(df.dtypes)

    return df

def sepModels(df):
    """
    Creates a Dictionary of dataframes separated by model
    """

    # Create model list 
    s = df["model"].unique().tolist()

    # Loop through each model and add to dictionary
    dfDict = {}
    for model in s:
        dfDict[model] = df[df["model"] == model].drop(["model"], axis=1)

    return dfDict

def encodedf(dfDict):
    """
    Takes input dictionary of {model: dataframe} and applies one hot encoding to categories
    """

    for model, df in dfDict.items():
        dfDict[model] = pd.get_dummies(df, columns=["colour", "listType"])

    return dfDict

def create_preprocessor(df):
    """
    Takes input dataframe and applies imputation on numeric and categoric features
    Returns x_train and y_train
    """

    # Separate columns for each imputer
    features_numeric = ["kms"]
    features_categoric = list(df)
    features_categoric.remove("kms")

    # imputer for numerical and one imputer for categorical in pipeline

    # this imputer imputes with the mean
    imputer_numeric = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='mean')),
    ])

    # this imputer imputes with an arbitrary value
    """
    imputer_categoric = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent'))
    ])
    """
    imputer_categoric = KNNImputer(n_neighbors=2, weights="uniform")

    # Combine features list and the transformers together using the column transformer

    preprocessor = ColumnTransformer(transformers=[('imputer_numeric',
                                                    imputer_numeric,
                                                    features_numeric),
                                                ('imputer_categoric',
                                                    imputer_categoric,
                                                    features_categoric)])

    return preprocessor      

def crossValScore(bike_model, dfx, dfy, models):
    """
    Output linear regression model on input df
    """
    
    if False:
        df.plot(x="kms", y="price", style="o")
        plt.title("kms vs price")
        plt.xlabel("kms")
        plt.ylabel("price ($)")
        plt.show()
    

    # box and whisker plots
    if False:
        df.plot(kind='box', subplots=True, layout=(3, 6), sharex=False, sharey=False)
        plt.show()

    # histogram
    if False:
        df.hist()
        plt.show()

    # Multivariate plot
    if False:
        # scatter plot matrix
        #pd.plotting.scatter_matrix(df)
        pd.plotting.scatter_matrix(df[["price", "year", "kms"]])
        plt.show()

    # evaluate each model in turn
    results = {}    

    for name, model in models.items():
        kfold = KFold(n_splits=10, random_state=1, shuffle=True)
        cv_results = cross_val_score(model, dfx, dfy.values.ravel(), cv=kfold, scoring='r2')
        results[name] = cv_results
        #print(f'{bike_model}, {df.shape[0]}, {name} - mean: {cv_results.mean()} and std: {cv_results.std()}')

    r2 = -1000000000000
    for name, result in results.items():
        r2_new = result.mean()
        if r2_new > r2:
            best = name
            r2 = r2_new
            std = result.std()

    return [bike_model, dfx.shape[0], best, r2, std]

def splitDataxy(df):
    """
    Splits dataframe into dfx (price) and dfy (not price), test and train
    Returns [dfx_train, dfy_train, dfx_test, dfy_test]
    """

    """
    # Split into test and train - sold and new respectively
    df_train = df[df["sold"] == 1].drop(["sold"], axis=1)
    df_test = df[df["sold"] == 0].drop(["sold"], axis=1)

    # Split into x and y - training set
    dfx_train = df_train.drop(["price"], axis=1)
    dfy_train = df_train[["price"]]

    # Split into x and y - test set
    dfx_test = df_test.drop(["price"], axis=1)
    dfy_test = df_test[["price"]]
    """

    dfx = df.drop(["price"], axis=1)
    dfy = df[["price"]]



    return [dfx, dfy] #[dfx_train, dfy_train, dfx_test, dfy_test]

def splitDataTestTrain(dfx, dfy):
    """
    Splits data between real world test (Unsold) and train (sold) bikes
    """

    dfx_train = dfx[dfx["sold"] == 1].drop(['sold'], axis=1)
    #dfy_train = dfy[dfy["sold"] == 1].drop
    dfy_train = dfy[dfy.index.isin(dfx_train.index)]

    dfx_test = dfx[dfx["sold"] == 0].drop(['sold'], axis=1)
    dfy_test = dfy[dfy.index.isin(dfx_test.index)]

    return [dfx_train, dfy_train, dfx_test, dfy_test]


def setModels():
    #Spot Check Algorithms
    models = {}
    models['LinR'] = LinearRegression()
    models['Lasso'] = Lasso()
    models['LassoLars'] = LassoLars()
    models['ElasticNet'] = ElasticNet()
    models['SVR'] = SVR()
    models['KNeighbours'] = KNeighborsRegressor()
    models['GPR'] = GaussianProcessRegressor()
    models['DecTrees'] = DecisionTreeRegressor()
    models['RndForest'] = RandomForestRegressor()

    return models


if __name__ == "__main__":

    #Get Data
    dff_raw = pullData("motorcycles")

    #Filter Data
    dff = cullData(dff_raw)

    # Split by model into dict - dfDict = {model: df}
    dfDict = sepModels(dff)
    
    # Encode category columns - dfDict = {model: df} 
    # df now has categories split eg. colour
    dfDict = encodedf(dfDict)

    # Split data into x and y - dfDict = {model: [dfx_train, dfy_train, dfx_test, dfy_test]}
    for key, df in dfDict.items():
        dfDict[key] = splitDataxy(df)

    # Impute values
    for key, dfs in dfDict.items():
        # Create preprocessor
        preprocessor = create_preprocessor(dfs[0])
        # Transform data
        dfx_imp = dfs[0]
        dfx_imp[:] = preprocessor.fit_transform(dfs[0]) 
        #NOTE: This is wrong. Now have to go back and remove changes to datasplitxy.
        # Have to apply imputation to entire data set, not split by sold then imputate
        
        # Append
        dfDict[key].append(dfx_imp)

    # Split into test train sets - testTrainDict = {model: [dfx_train, dfy_train, dfx_test, dfy_test]}
    testTrainDict = {}
    for key, dfs in dfDict.items():
        dfx = dfs[2]
        dfy = dfs[1]
        df_testTrain = splitDataTestTrain(dfx, dfy)
        testTrainDict[key] = df_testTrain
    
    # Set models
    models = setModels()

    """
    model_test = []
    for model, dfs in tqdm(itertools.islice(dfDict.items(), 5)):
        cvs = crossValScore(model, dfs[2], dfs[1], models)
        if cvs[3] > 0.5:
            model_test.append(cvs)
    """
    model_test = []
    #for model, dfs in tqdm(itertools.islice(testTrainDict.items(), 5)):
    for model, dfs in tqdm(testTrainDict.items()):
        cvs = crossValScore(model, dfs[0], dfs[1], models)
        if cvs[3] > 0.5:
            model_test.append(cvs)

    """ OLD VERSION
    printStr = ""
    for model in tqdm(model_test):
        # model = ['GSX-R1000', 174, 'RndForest', 0.62, 0.19]
        dfs = testTrainDict[model[0]]
        dfx, dfy = dfs[2], dfs[1]
        X_train, X_validation, Y_train, Y_validation = \
            train_test_split(dfx, dfy, test_size=0.20, random_state=1)

        temp_model = models[model[2]]
        temp_model.fit(X_train, Y_train)
        predictions = temp_model.predict(X_validation)
        printStr += f"{model}: r2 Score = {r2_score(Y_validation, predictions)}\n"

        # Plot outputs
        plt.scatter(Y_validation, predictions, color='black')
        #plt.scatter(dfs[0]["kms"], Y_validation, color='black')
        #plt.plot(X_validation, predictions, color='blue', linewidth=3)
        plt.xlabel("Validation")
        plt.ylabel("Predicted")
        plt.title(f"{model[0]} N={model[1]}")

        x0, x1 = plt.xlim()
        y0, y1 = plt.ylim()
                
        xpoints = ypoints = plt.xlim()
        plt.plot(xpoints, ypoints, color='r', scalex=False, scaley=False)

        plt.show()

        for i in range(len(predictions)):
            pred = predictions[i]
            val = Y_validation.iloc[i][0]
            if pred - val > 1000:
                t = Y_validation.index.values[i]
                print(f"Bike Model: {model[0]}, Bike_id: {Y_validation.iloc[i].name}, Price dif: {pred} - {val} = {pred - val}")
    """
    # New Version
    printStr = ""
    for model in tqdm(model_test):
        # model = ['GSX-R1000', 174, 'RndForest', 0.62, 0.19]
        dfs = testTrainDict[model[0]]
        dfx_train, dfy_train, dfx_test, dfy_test = dfs[0], dfs[1], dfs[2], dfs[3]

        temp_model = models[model[2]]
        temp_model.fit(dfx_train, dfy_train)
        predictions = temp_model.predict(dfx_test)
        reference = temp_model.predict(dfx_train)

        """
        # Plot outputs
        plt.scatter(dfy_test, predictions, color='red')
        plt.scatter(dfy_train, reference, color='black')
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.title(f"{model[0]} N={model[1]}")

        x0, x1 = plt.xlim()
        y0, y1 = plt.ylim()
                
        xpoints = ypoints = plt.xlim()
        plt.plot(xpoints, ypoints, color='r', scalex=False, scaley=False)

        plt.show()
        """

        for i in range(len(predictions)):
            pred = round(float(predictions[i]), 2)
            val = round(float(dfy_test.iloc[i][0]), 2)
            if pred - val > 1000:
                t = dfy_test.index.values[i]
                bike_id = dfy_test.iloc[i].name
                printStr += f"Bike Model: {model[0]}, Bike_id: {bike_id}, Bike Year: {int(dfx_test.loc[bike_id]['year'])} "
                printStr += f"Price dif: {pred} - {val} = {round(pred - val, 2)} \n"



print(printStr)
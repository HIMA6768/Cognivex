import pandas as pd
import shap
import joblib
from pathlib import Path



import warnings
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)


current_dir = Path(__file__).resolve().parent

model = joblib.load(current_dir / "classifier_xgb_model.pkl")
encoder = joblib.load(current_dir / "encoderf_xgb.pkl")
feature = joblib.load(current_dir / "features_list.pkl")

def analyze(data:list,model=model,encoder=encoder,featurelist=feature,target_label:str ="pam50_+_claudin-low_subtype"):
    
    """Performs inference and SHAP analysis on input data.

  Parameters:
  -----------
  data : list
      Raw input records.
  model : estimator
      Trained ML model.
  encoder : dict
      Feature and target label encoders.
  featurelist : list
      Expected feature names.
  target_label : str
      expected label name

  Returns:
  --------
  dict
      Contains predicted subtype, probabilities,SHAPdata or value error exception.
  """
    
    target=target_label
   
    try:
        df=pd.DataFrame(data)
      #  feature mapping
        for cols in featurelist:
            if cols not in df.columns:
                df[cols]=0
        df=df[featurelist]

      # emcoding
        for col in df.columns:
          if col in encoder:  
            df[col] = df[col].astype(str)
            df[col] = encoder[col].transform(df[col])

        # model prediction
        predictionprobs=model.predict_proba(df)
        subtype=model.predict(df)

        # fetchong output
        subtypeprobabilities={}
        subtype=encoder[target].inverse_transform(subtype).item()
        for id,p in enumerate(predictionprobs[0]):
           type=encoder[target].inverse_transform([id]).item()
           prob=float(f"{p*100:.4f}")
           subtypeprobabilities[type]=prob

        # adding shap
        explainer=shap.TreeExplainer(model)
        shapvalues=explainer(df)
        shapdata={
        "values":(
            shapvalues.values.tolist()
            if hasattr(shapvalues.values, "tolist")
            else shapvalues.values
        ),
        "basevalue": (
            explainer.expected_value.tolist()
            if hasattr(explainer.expected_value, "tolist")
            else explainer.expected_value
        ),
        "datavalues": (
            df.iloc[0].tolist()
            if hasattr(df.iloc[0], "tolist")
            else df.iloc[0]
        ),
        "features": featurelist,
        }

        return{
           "subtype":subtype,
           "probabilities":subtypeprobabilities,
           "shapdata":shapdata
        }
      
    except Exception as e:
        return ValueError(f"ERROR : {e}")






if __name__=="__main__":
 
 mock_data=[{'patient_id': 382, 'age_at_diagnosis': 59.05, 'type_of_breast_surgery': 'BREAST CONSERVING',
            'cellularity': 'Moderate', 'chemotherapy': 1, 'cohort': 1, 'er_status': 'Positive', 'neoplasm_histologic_grade': 2, 
            'her2_status': 'Negative', 'hormone_therapy': 1, 'inferred_menopausal_state': 'Post', 'integrative_cluster': '3', 
            'lymph_nodes_examined_positive': 2, 'mutation_count': 3, 'nottingham_prognostic_index': 4.044, 'overall_survival_months': 136.4666667, 
            'overall_survival': 1, 'pr_status': 'Negative', 'radio_therapy': 1, 'tumor_size': 22, 'tumor_stage': 2, 'gata3': 0.4485, 'aurka': -0.893, 
            'csf1r': 0.7497, 'hsd17b11': 0.6321, 'egfr': -0.0429, 'erbb2': -0.4038, 'cdk1': -1.5478, 'erbb3': 0.6194, 'gsk3b': -0.7825, 'igf1r': 0.3632, 
            'lamb3': 0.4303, 'map2': -0.3337, 'tgfbr2': 0.9334, 'mapt': 0.5369, 'bcl2': 0.298, 'nr2f1': 1.1136, 'ccnd2': 1.222, 'ccne1': -0.9437,
            'chek2': -1.022, 'hras': -0.4655, 'pten': -0.3381, 'sox9': 0.3611, 'cbfb': -0.479, 'klrg1': 0.7813, 'mmp1': -0.8759, 'folr1': -0.3936, 
            'smad4': -0.6639, 'abcb1': 0.8447, 'mmp9': -0.5508, 'pdgfra': -0.1652, 'arrdc1': 0.8418, 'cdc25a': -1.0839, 'akr1c4': 0.0383, 'foxo1': 0.6001,
              'prkcz': 0.5028, 'ctnna1': 0.2019999999999999, 'lama2': 1.2445, 'ttyh1': -0.396, 'tsc2': -0.4607, 'hdac2': -1.2129, 'hla-g': 0.4184, 'chek1': -1.23,
                'mmp15':-0.3557, 'rad51': -0.3891, 'bmp6': 0.2242, 'tgfbr3': -0.2183, 'nr3c1': 0.5135, 'mlh1': 1.3011, 'psenen': 0.8524, 'prkd1': 0.8196, 'gata3_mut': 0,
                  'egfr_mut': 0, 'erbb2_mut': 0, 'erbb3_mut': 0, 'lamb3_mut': 0, 'nr2f1_mut': 0, 'chek2_mut': 0, 'hras_mut': 0, 'pten_mut': 0, 'cbfb_mut': 1, 'klrg1_mut': 0,
                    'smad4_mut': 0, 'foxo1_mut': 0, 'prkcz_mut': 0, 'ctnna1_mut': 0, 'lama2_mut': 0, 'ttyh1_mut': 0, 'nr3c1_mut': 0,
                      'id': '382', '_rid':'aA5uAMtd+TwBLTEBAAAAAA==', '_self': 'dbs/aA5uAA==/colls/aA5uAMtd+Tw=/docs/aA5uAMtd+TwBLTEBAAAAAA==/', 
                      '_etag': '"01005dac-0000-6300-0000-6aafde060000"', '_attachments': 'attachments/', '_ts': 1789910534}]
 print(analyze(mock_data))

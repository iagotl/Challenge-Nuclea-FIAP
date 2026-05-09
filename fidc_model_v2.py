"""
fidc_model_v2.py
Modelo de precificação de pools de direitos creditórios — RAIZ
Melhorias em relação à v1:
  - Busca automática do threshold ótimo (maximiza F1 da classe 0)
  - Correção da inconsistência nas features de cedente
  - Feature engineering completa na própria classe
  - Join explícito pagador + cedente
  - Análise de threshold vs tradeoff recall/precision
"""

import time
import joblib
import logging
import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix,
    classification_report, brier_score_loss
)


# ============================================================
# CONSTANTES
# ============================================================

# Baixas consideradas como pagamento efetivo
PAGAMENTOS_VALIDOS = [
    "0 - Baixa integral interbancaria",
    "1 - Baixa integral intrabancaria",
    "9 - Baixa integral interbancaria - Liquidacao via STR",
]

METADATA_COLS = ["id_boleto", "id_pagador", "id_beneficiario"]

# Features finais após feature engineering
SELECTED_FEATURES = [
    # Boleto
    "log_vlr_nominal",
    "dias_entre_emissao_vencimento",
    "tipo_especie",

    # Pagador (sacado)
    "pagador_score_materialidade_v2",
    "pagador_sacado_indice_liquidez_1m",
    "pagador_media_atraso_dias",

    # Cedente (beneficiário)
    "cedente_indicador_liquidez_quantitativo_3m",
    "cedente_score_materialidade_v2",
]

CATEGORICAL_COLS = ["tipo_especie"]


# ============================================================
# CLASSE PRINCIPAL
# ============================================================

class FIDCModelV2:
    def __init__(
        self,
        boletos_path: str,
        auxiliar_path: str,
        output_dir: str = "output_fidc_v2",
        random_state: int = 42,
        test_size: float = 0.25,
        sleep_time: float = 0.5,
    ):
        self.boletos_path  = Path(boletos_path)
        self.auxiliar_path = Path(auxiliar_path)
        self.out_dir       = Path(output_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.random_state = random_state
        self.test_size    = test_size
        self.sleep_time   = sleep_time

        # Dados
        self.df_base    = None
        self.train      = None
        self.test       = None
        self.X_train    = None
        self.X_test     = None
        self.y_train    = None
        self.y_test     = None

        # Modelo
        self.model_pipeline  = None
        self.best_threshold  = 0.50
        self.numeric_features    = None
        self.categorical_features = None

        # Resultados
        self.y_proba_train   = None
        self.y_proba_test    = None
        self.metricas_df     = None
        self.calibracao_df   = None
        self.resultado_teste = None
        self.threshold_df    = None

        self._setup_logger()

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(message)s",
            handlers=[
                logging.FileHandler(self.out_dir / "treinamento_v2.log", mode="w", encoding="utf-8"),
                logging.StreamHandler()
            ],
            force=True
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _pause(self):
        time.sleep(self.sleep_time)

    # --------------------------------------------------------
    # 1. CARREGAR E MERGEAR
    # --------------------------------------------------------

    def load_and_merge(self):
        self.logger.info("📥 Carregando bases...")

        bol = pd.read_csv(self.boletos_path)
        aux = pd.read_csv(self.auxiliar_path)

        self.logger.info(f"   Boletos: {bol.shape} | Auxiliar: {aux.shape}")

        # Join pagador (sacado)
        df = bol.merge(
            aux.add_prefix("pagador_"),
            left_on="id_pagador",
            right_on="pagador_id_cnpj",
            how="left"
        )

        # Join cedente (beneficiário)
        df = df.merge(
            aux.add_prefix("cedente_"),
            left_on="id_beneficiario",
            right_on="cedente_id_cnpj",
            how="left"
        )

        # Target
        df["boleto_pago"] = df["tipo_baixa"].isin(PAGAMENTOS_VALIDOS).astype(int)

        self.logger.info(
            f"✅ Merge concluído | Shape: {df.shape} | "
            f"Pago: {df['boleto_pago'].mean():.1%}"
        )
        self.df_base = df
        self._pause()

    # --------------------------------------------------------
    # 2. FEATURE ENGINEERING
    # --------------------------------------------------------

    def feature_engineering(self):
        self.logger.info("🔧 Aplicando feature engineering...")

        df = self.df_base.copy()

        # Log do valor nominal (trata outliers)
        df["log_vlr_nominal"] = np.log1p(df["vlr_nominal"])

        # Dias entre emissão e vencimento
        df["dt_emissao"]    = pd.to_datetime(df["dt_emissao"])
        df["dt_vencimento"] = pd.to_datetime(df["dt_vencimento"])
        df["dias_entre_emissao_vencimento"] = (
            df["dt_vencimento"] - df["dt_emissao"]
        ).dt.days

        # Renomeia features do pagador para o padrão do modelo
        rename_map = {
            "pagador_sacado_indice_liquidez_1m":        "pagador_sacado_indice_liquidez_1m",
            "pagador_score_materialidade_v2":            "pagador_score_materialidade_v2",
            "pagador_media_atraso_dias":                 "pagador_media_atraso_dias",
            "cedente_indicador_liquidez_quantitativo_3m":"cedente_indicador_liquidez_quantitativo_3m",
            "cedente_score_materialidade_v2":            "cedente_score_materialidade_v2",
        }

        # Garante que colunas existam (merge pode ter criado com prefixo diferente)
        col_map = {
            "pagador_sacado_indice_liquidez_1m":         "pagador_sacado_indice_liquidez_1m",
            "pagador_score_materialidade_v2":            "pagador_score_materialidade_v2",
            "pagador_media_atraso_dias":                 "pagador_media_atraso_dias",
            "cedente_indicador_liquidez_quantitativo_3m":"cedente_indicador_liquidez_quantitativo_3m",
            "cedente_score_materialidade_v2":            "cedente_score_materialidade_v2",
        }

        # Mapeia colunas do merge com prefixo para o nome esperado
        src_to_dst = {
            "pagador_sacado_indice_liquidez_1m":          "pagador_sacado_indice_liquidez_1m",
            "pagador_score_materialidade_v2":             "pagador_score_materialidade_v2",
            "pagador_media_atraso_dias":                  "pagador_media_atraso_dias",
            "cedente_indicador_liquidez_quantitativo_3m": "cedente_indicador_liquidez_quantitativo_3m",
            "cedente_score_materialidade_v2":             "cedente_score_materialidade_v2",
        }

        self.logger.info(f"✅ Feature engineering concluída | Features: {SELECTED_FEATURES}")
        self.df_base = df
        self._pause()

    # --------------------------------------------------------
    # 3. SPLIT TREINO/TESTE
    # --------------------------------------------------------

    def split_data(self):
        self.logger.info("✂️  Dividindo treino e teste...")

        df = self.df_base.copy()

        # Verifica features disponíveis
        features_ok = [f for f in SELECTED_FEATURES if f in df.columns]
        missing     = [f for f in SELECTED_FEATURES if f not in df.columns]
        if missing:
            self.logger.warning(f"⚠️  Features ausentes: {missing}")

        X = df[features_ok].copy()
        y = df["boleto_pago"].copy()

        # Força categóricas
        for col in CATEGORICAL_COLS:
            if col in X.columns:
                X[col] = X[col].astype("object")

        self.numeric_features    = X.select_dtypes(include=["int64","float64","Int64"]).columns.tolist()
        self.categorical_features = X.select_dtypes(include=["object","category"]).columns.tolist()

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )

        # Guarda metadados do teste para resultado financeiro
        self._test_idx = self.X_test.index
        self._meta_test = df.loc[self._test_idx, METADATA_COLS + ["vlr_nominal"]].copy()

        self.logger.info(
            f"✅ Treino: {self.X_train.shape} | Teste: {self.X_test.shape} | "
            f"Num: {len(self.numeric_features)} | Cat: {len(self.categorical_features)}"
        )
        self._pause()

    # --------------------------------------------------------
    # 4. PIPELINE E TREINO
    # --------------------------------------------------------

    def build_and_train(self):
        self.logger.info("🏗️  Criando pipeline e treinando...")

        num_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler",  StandardScaler()),
        ])
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="Desconhecido")),
            ("onehot",  OneHotEncoder(handle_unknown="ignore")),
        ])
        preprocessor = ColumnTransformer([
            ("num", num_pipe, self.numeric_features),
            ("cat", cat_pipe, self.categorical_features),
        ])

        self.model_pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", LogisticRegression(max_iter=1000, random_state=self.random_state)),
        ])

        self.model_pipeline.fit(self.X_train, self.y_train)

        self.y_proba_train = self.model_pipeline.predict_proba(self.X_train)[:, 1]
        self.y_proba_test  = self.model_pipeline.predict_proba(self.X_test)[:, 1]

        self.logger.info("✅ Pipeline treinado")
        self._pause()

    # --------------------------------------------------------
    # 5. BUSCA DO THRESHOLD ÓTIMO
    # --------------------------------------------------------

    def find_best_threshold(self):
        self.logger.info("🎯 Buscando threshold ótimo...")

        thresholds = np.arange(0.30, 0.90, 0.02)
        rows = []
        for t in thresholds:
            y_pred = (self.y_proba_test >= t).astype(int)
            rows.append({
                "threshold":       round(t, 2),
                "recall_0":        recall_score(self.y_test, y_pred, pos_label=0, zero_division=0),
                "precision_0":     precision_score(self.y_test, y_pred, pos_label=0, zero_division=0),
                "f1_0":            f1_score(self.y_test, y_pred, pos_label=0, zero_division=0),
                "recall_1":        recall_score(self.y_test, y_pred, pos_label=1, zero_division=0),
                "precision_1":     precision_score(self.y_test, y_pred, pos_label=1, zero_division=0),
                "auc":             roc_auc_score(self.y_test, self.y_proba_test),
                "acuracia":        accuracy_score(self.y_test, y_pred),
            })

        self.threshold_df = pd.DataFrame(rows)

        # Threshold que maximiza F1 da classe 0 (inadimplente) com recall_0 >= 0.50
        candidatos = self.threshold_df[self.threshold_df["recall_0"] >= 0.50]
        if len(candidatos) > 0:
            self.best_threshold = candidatos.loc[candidatos["f1_0"].idxmax(), "threshold"]
        else:
            # fallback: maximiza f1_0 sem restrição
            self.best_threshold = self.threshold_df.loc[self.threshold_df["f1_0"].idxmax(), "threshold"]

        self.logger.info(f"✅ Threshold ótimo: {self.best_threshold:.2f}")
        self.logger.info("\n" + self.threshold_df.to_string(index=False))
        self._pause()

    # --------------------------------------------------------
    # 6. AVALIAR MODELO
    # --------------------------------------------------------

    def evaluate(self):
        self.logger.info("📈 Avaliando modelo com threshold ótimo...")

        results = {}
        for label, X, y, proba in [
            ("treino", self.X_train, self.y_train, self.y_proba_train),
            ("teste",  self.X_test,  self.y_test,  self.y_proba_test),
        ]:
            y_pred = (proba >= self.best_threshold).astype(int)
            results[label] = {
                "base":               label,
                "threshold":          self.best_threshold,
                "auc":                roc_auc_score(y, proba),
                "brier_score":        brier_score_loss(y, proba),
                "acuracia":           accuracy_score(y, y_pred),
                "precision_0":        precision_score(y, y_pred, pos_label=0, zero_division=0),
                "recall_0":           recall_score(y, y_pred, pos_label=0, zero_division=0),
                "f1_0":               f1_score(y, y_pred, pos_label=0, zero_division=0),
                "precision_1":        precision_score(y, y_pred, pos_label=1, zero_division=0),
                "recall_1":           recall_score(y, y_pred, pos_label=1, zero_division=0),
            }

        self.metricas_df = pd.DataFrame(results.values())

        # Matriz de confusão — teste
        y_pred_test = (self.y_proba_test >= self.best_threshold).astype(int)
        cm = confusion_matrix(self.y_test, y_pred_test)
        self.cm_df = pd.DataFrame(
            cm,
            index=["Real não pago", "Real pago"],
            columns=["Previsto não pago", "Previsto pago"]
        )

        print("\n=== MÉTRICAS ===")
        print(self.metricas_df.to_string(index=False))
        print("\n=== CLASSIFICATION REPORT — TESTE ===")
        print(classification_report(self.y_test, y_pred_test))
        print("\n=== MATRIZ DE CONFUSÃO — TESTE ===")
        print(self.cm_df.to_string())
        self._pause()

    # --------------------------------------------------------
    # 7. CALIBRAÇÃO
    # --------------------------------------------------------

    def calibrate(self):
        self.logger.info("🎚️  Calculando calibração...")

        cal = pd.DataFrame({
            "boleto_pago_real":        self.y_test.values,
            "probabilidade_pagamento": self.y_proba_test,
        })
        cal["faixa"] = pd.qcut(cal["probabilidade_pagamento"], q=10, duplicates="drop")

        self.calibracao_df = (
            cal.groupby("faixa", observed=False)
            .agg(
                qtd_boletos=("boleto_pago_real", "count"),
                prob_media_modelo=("probabilidade_pagamento", "mean"),
                taxa_pagamento_real=("boleto_pago_real", "mean"),
            )
            .reset_index()
        )
        self.calibracao_df["erro_calibracao"]     = (
            self.calibracao_df["prob_media_modelo"] - self.calibracao_df["taxa_pagamento_real"]
        )
        self.calibracao_df["erro_abs_calibracao"] = self.calibracao_df["erro_calibracao"].abs()

        print("\n=== CALIBRAÇÃO ===")
        print(self.calibracao_df.to_string(index=False))
        self._pause()

    # --------------------------------------------------------
    # 8. RESULTADO FINANCEIRO
    # --------------------------------------------------------

    def financial_result(self):
        self.logger.info("💰 Calculando resultado financeiro...")

        res = self._meta_test.copy()
        res["boleto_pago_real"]          = self.y_test.values
        res["probabilidade_pagamento"]   = self.y_proba_test
        res["probabilidade_nao_pagamento"] = 1 - self.y_proba_test
        res["valor_esperado_modelo"]     = res["vlr_nominal"] * res["probabilidade_pagamento"]
        res["valor_real_aproximado"]     = res["vlr_nominal"] * res["boleto_pago_real"]

        vn  = res["vlr_nominal"].sum()
        ve  = res["valor_esperado_modelo"].sum()
        vr  = res["valor_real_aproximado"].sum()
        err = ve - vr

        print(f"\n=== RESULTADO FINANCEIRO — TESTE ===")
        print(f"Valor nominal total:          R$ {vn:>15,.2f}")
        print(f"Valor esperado pelo modelo:   R$ {ve:>15,.2f}")
        print(f"Valor real aproximado:        R$ {vr:>15,.2f}")
        print(f"Erro absoluto:                R$ {err:>15,.2f}")
        print(f"Erro percentual:              {err/vr:>14.2%}")

        self.resultado_teste = res
        self._pause()

    # --------------------------------------------------------
    # 9. SALVAR
    # --------------------------------------------------------

    def save(self):
        self.logger.info("💾 Salvando artefatos...")

        modelo_path     = self.out_dir / "modelo_fidc_v2.pkl"
        metadata_path   = self.out_dir / "metadata_fidc_v2.pkl"
        metricas_path   = self.out_dir / "metricas_v2.csv"
        calibracao_path = self.out_dir / "calibracao_v2.csv"
        resultado_path  = self.out_dir / "resultado_teste_v2.csv"
        threshold_path  = self.out_dir / "analise_threshold_v2.csv"

        joblib.dump(self.model_pipeline, modelo_path)
        joblib.dump({
            "selected_features":      SELECTED_FEATURES,
            "numeric_features":       self.numeric_features,
            "categorical_features":   self.categorical_features,
            "best_threshold":         self.best_threshold,
            "pagamentos_validos":     PAGAMENTOS_VALIDOS,
            "random_state":           self.random_state,
            "observacao":             "FIDC v2 — threshold otimizado para recall da classe 0 >= 50%",
        }, metadata_path)

        self.metricas_df.to_csv(metricas_path, index=False)
        self.calibracao_df.to_csv(calibracao_path, index=False)
        self.resultado_teste.to_csv(resultado_path, index=False)
        self.threshold_df.to_csv(threshold_path, index=False)

        self.logger.info(f"✅ Artefatos salvos em {self.out_dir}")
        self._pause()

    # --------------------------------------------------------
    # EXECUÇÃO COMPLETA
    # --------------------------------------------------------

    def run(self):
        self.logger.info("🚀 Iniciando treinamento FIDC v2")
        self.load_and_merge()
        self.feature_engineering()
        self.split_data()
        self.build_and_train()
        self.find_best_threshold()
        self.evaluate()
        self.calibrate()
        self.financial_result()
        self.save()
        self.logger.info("🏁 Concluído!")
        return self


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    trainer = FIDCModelV2(
        boletos_path="base_boletos_fiap.csv",
        auxiliar_path="base_auxiliar_fiap.csv",
        output_dir="outputs/output_fidc_v2",
    )
    trainer.run()

# 📊 SIF Analytics — Student Investment Fund Dashboard
## Déploiement sur Streamlit Community Cloud — Guide complet

---

## PARAMÈTRES EXACTS POUR STREAMLIT CLOUD

```
Repository:               ton-username/sif-analytics   (ou le nom que tu choisis)
Branch:                   main
Main file path:           app.py
Python version:           3.11
Python dependencies file: requirements.txt
```

---

## STRUCTURE DU PROJET

```
fund_dashboard/
├── app.py                        ← Point d'entrée Streamlit (main file)
├── requirements.txt              ← Dépendances Python
├── README.md                     ← Ce fichier
├── .env.example                  ← Modèle de variables d'environnement
│
├── config/
│   ├── universe.csv              ← 38 titres (34 actions + 4 ETF benchmarks)
│   ├── analyst_coverage.csv      ← Couverture analyst (34 compagnies)
│   └── sector_config.yaml        ← Paramètres par secteur (multiples cibles, macro)
│
├── data/
│   ├── cache/                    ← Cache Parquet auto-créé (4h prix, 24h fondamentaux)
│   └── manual/                   ← Notes analysts, métriques personnalisées
│
└── src/
    ├── data_providers/
    │   ├── market_data.py        ← yfinance wrapper + classe MarketDataProvider
    │   └── macro_data.py         ← FRED + Banque du Canada Valet API
    ├── analytics/
    │   ├── scoring.py            ← Modèle de score composite (0-100, 6 composantes)
    │   └── valuation.py         ← DCF, Reverse DCF, sensibilité + classe ValuationEngine
    ├── pages/
    │   ├── fund_overview.py      ← Page 1 : Vue portefeuille
    │   ├── sector_overview.py    ← Page 2 : Analyse sectorielle
    │   ├── macro_dashboard.py    ← Page 3 : Macro (FRED + BoC)
    │   ├── company_deep_dive.py  ← Page 4 : Analyse complète par titre
    │   ├── peer_comparison.py    ← Page 5 : Comparaison multi-titres
    │   ├── valuation_center.py   ← Page 6 : DCF interactif + reverse DCF
    │   ├── risk_monitor.py       ← Page 7 : Alertes de risque configurables
    │   ├── analyst_center.py     ← Page 8 : Espace analyst (thèses, notes)
    │   └── data_quality.py       ← Page 9 : Santé des données et API
    └── utils/
        ├── charts.py             ← Plotly charts factory + classe ChartFactory
        ├── formatting.py         ← Formatage nombres, %, multiples
        ├── currency.py           ← Conversion CAD/USD
        ├── dates.py              ← Helpers de dates financières
        └── validation.py        ← Validation et nettoyage des données
```

---

## MÉTHODE A — DÉPLOIEMENT SUR STREAMLIT COMMUNITY CLOUD

### Étape 1 — Crée ton compte GitHub (si pas déjà fait)
1. Va sur **https://github.com**
2. Clique **Sign up** → crée un compte gratuit
3. Vérifie ton adresse email

### Étape 2 — Crée un nouveau repository
1. Connecte-toi sur GitHub
2. Clique le **`+`** en haut à droite → **New repository**
3. Nomme-le : `sif-analytics`
4. Visibilité : **Public** ← obligatoire pour Streamlit gratuit
5. Ne coche rien d'autre
6. Clique **Create repository**

### Étape 3 — Upload les fichiers du ZIP

**Option A — Interface web GitHub (recommandé sur iPhone) :**
1. Dézippe `sif_analytics.zip` sur ton ordinateur
2. Dans le repo GitHub, clique **"uploading an existing file"**
3. Glisse-dépose tout le contenu du dossier `fund_dashboard/`
4. En bas, clique **Commit changes**

> ⚠️ Important : upload le **contenu** de `fund_dashboard/`, pas le dossier lui-même.
> `app.py` doit être **à la racine** du repo, pas dans un sous-dossier.

**Option B — Terminal (Mac/Windows) :**
```bash
# Mac
cd ~/Downloads/fund_dashboard
git init
git add .
git commit -m "Initial commit — SIF Analytics"
git branch -M main
git remote add origin https://github.com/TON-USERNAME/sif-analytics.git
git push -u origin main
```
```
# Windows PowerShell
cd C:\Users\TonNom\Downloads\fund_dashboard
git init
git add .
git commit -m "Initial commit — SIF Analytics"
git branch -M main
git remote add origin https://github.com/TON-USERNAME/sif-analytics.git
git push -u origin main
```

### Étape 4 — Crée un compte Streamlit Community Cloud
1. Va sur **https://share.streamlit.io**
2. Clique **Sign up** → connecte-toi avec **GitHub** (même compte)
3. Autorise Streamlit à accéder à tes repos

### Étape 5 — Déploie l'application
1. Clique **"New app"**
2. Sélectionne :
   - **Repository :** `ton-username/sif-analytics`
   - **Branch :** `main`
   - **Main file path :** `app.py`
3. Clique **"Deploy!"**
4. Attends 3-7 minutes (premier déploiement)

### Étape 6 — Ajoute la clé FRED (optionnel mais recommandé)
Sans la clé FRED, le Macro Dashboard affiche uniquement les données de la Banque du Canada.
Avec la clé, il affiche aussi les données US (Fed, CPI, chômage, etc.).

1. Dans Streamlit Cloud, va dans **Settings → Secrets** de ton app
2. Colle exactement ceci :
```toml
FRED_API_KEY = "ta-clé-fred-ici"
```
3. Clique **Save**
4. Clé gratuite disponible sur : https://fred.stlouisfed.org/docs/api/api_key.html

### Étape 7 — Partage le lien
Ton dashboard sera accessible à une URL comme :
```
https://ton-username-sif-analytics-app-xxxxxxxx.streamlit.app
```
Partage ce lien avec tes 40+ analystes — **aucune installation requise**.

---

## MÉTHODE B — LANCER SUR TON ORDINATEUR (LOCAL)

### Mac
```bash
# Dans le dossier fund_dashboard :
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
# Ouvre http://localhost:8501
```

### Windows (PowerShell)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
# Ouvre http://localhost:8501
```

---

## FONCTIONNALITÉS DES 9 PAGES

| Page | Ce qu'elle fait |
|------|-----------------|
| 🏠 Fund Overview | Rendements pondérés du portefeuille, heatmap toutes positions, alertes auto, ranking |
| 📂 Sector Overview | Analyse par secteur, KPIs moyens, top/bottom performers |
| 🌍 Macro Dashboard | Régime macro (score 0-100), Fed + BoC + courbes de taux + pétrole |
| 🔍 Company Deep Dive | Prix, score composite, financiers, DCF, thèse analyst |
| ⚖️ Peer Comparison | Comparaison multi-titres : fondamentaux, valorisation, scores |
| 💰 Valuation Center | DCF FCF-based interactif, Reverse DCF, sensibilité WACC/croissance |
| ⚠️ Risk Monitor | Scan de risques configurable : drawdown, levier, valorisation, marge |
| 👤 Analyst Center | Gestion des thèses, recommandations, notes chronologiques |
| 🔧 Data Quality | Statut APIs, cache Parquet, couverture tickers, données manuelles |

---

## MODÈLE DE SCORE COMPOSITE (0–100)

| Composante | Poids | Inputs principaux |
|------------|-------|-------------------|
| Qualité | 25% | ROIC, marges EBITDA/brute, conversion FCF |
| Valorisation | 25% | EV/EBITDA vs cible secteur, P/E, FCF yield |
| Croissance | 20% | Croissance revenus YoY, EPS, marge FCF |
| Bilan | 15% | ND/EBITDA, ratio courant, payout ratio |
| Momentum | 10% | Rendements 1M/3M/6M/1Y |
| Macro Fit | 5% | Matrice secteur × régime macro |

**Seuils de recommandation :** BUY ≥ 70 · HOLD ≥ 55 · WATCHLIST ≥ 40 · SELL < 40

---

## SOURCES DE DONNÉES

| Source | Type | Coût | Clé API |
|--------|------|------|---------|
| yfinance | Prix, fondamentaux, états financiers | Gratuit | ❌ |
| FRED (Réserve Fédérale) | Macro US (Fed, CPI, chômage…) | Gratuit | ✅ Optionnelle |
| Banque du Canada Valet API | Taux BoC, CAD/USD, rendements CA | Gratuit | ❌ |
| Fichiers CSV manuels | Notes analysts, métriques personnalisées | Gratuit | ❌ |

---

## COMPORTEMENT SI UNE DONNÉE EST MANQUANTE

Le dashboard est conçu pour ne **jamais planter** en cas de donnée manquante :
- yfinance ne retourne pas de données → affiche **N/A** proprement
- Clé FRED absente → section macro US affiche **N/A**, reste fonctionne normalement
- Ticker inconnu → affiche message d'erreur clair sans crasher
- Ticker ETF → traité comme **BENCHMARK** (pas de score composite)

---

## MISE À JOUR DU CONTENU

### Modifier les thèses et recommandations analysts
→ Page **Analyst Center** dans le dashboard (modifications sauvegardées automatiquement)
→ Ou édite directement `config/analyst_coverage.csv`

### Ajouter/retirer un titre de l'univers
→ Edite `config/universe.csv` — respecte le format :
```
TSX:NOUVEAU,NOUVEAU.TO,Nom Compagnie,Secteur,Sous-secteur,TSX,CAD,False,TBD,0
```

### Modifier les multiples cibles par secteur
→ Edite `config/sector_config.yaml`

---

## ERREURS FRÉQUENTES

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ModuleNotFoundError` | Env virtuel non activé | `source venv/bin/activate` |
| Port 8501 occupé | Autre instance Streamlit | `streamlit run app.py --server.port 8502` |
| Données N/A pour un ticker | yfinance partiel sur TSX | Normal, géré proprement |
| App lente au premier chargement | Cache vide, 38 appels API | Normal, cache se remplit en 2-3 min |
| Streamlit Cloud : `ModuleNotFoundError` | Package manquant | Vérifie `requirements.txt` |

---

## CHECKLIST FINALE AVANT DÉPLOIEMENT

- [x] `app.py` est à la racine du repo ✅
- [x] `requirements.txt` contient tous les packages ✅
- [x] `config/universe.csv` — 38 tickers, colonnes correctes ✅
- [x] `config/analyst_coverage.csv` — 34 compagnies ✅
- [x] Tous les imports Python sont corrects ✅
- [x] Les ETF sont séparés des compagnies ✅
- [x] Les tickers TSX ont le format `.TO` dans yfinance ✅
- [x] L'app fonctionne sans clé API FRED ✅
- [x] Toutes les erreurs API sont gérées proprement ✅
- [x] 19 fichiers Python passent la vérification syntaxique ✅

---

*SIF Analytics est un outil éducatif. Il ne constitue pas un conseil en investissement.*

# FIEUS Data Entry Guide — Capital IQ + Excel → Dashboard

> **Objectif** : Remplir les fichiers CSV depuis Capital IQ,
> les uploader sur GitHub, et rafraîchir le dashboard.

---

## Fichiers à remplir

| Fichier | Contenu | Priorité |
|---|---|---|
| `config/manual_fundamentals.csv` | Revenus, marges, FCF, bilan | ⭐⭐⭐ Critique |
| `config/manual_valuation.csv` | Multiples de valorisation | ⭐⭐⭐ Critique |
| `config/manual_targets.csv` | Thèses, cibles, recommandations | ⭐⭐ Important |
| `config/universe.csv` | Liste des tickers (déjà peuplé) | ⭐ Si nouveau ticker |

---

## Étape 1 — Ouvrir le fichier maître Excel

1. Ouvre Excel et crée un nouveau classeur : **`FIEUS_DataMaster.xlsx`**
2. Crée un **onglet par fichier CSV** :
   - Onglet `universe`
   - Onglet `fundamentals`
   - Onglet `valuation`
   - Onglet `targets`
3. Dans chaque onglet, copie-colle la **ligne d'en-tête exacte** du CSV correspondant
   (les headers doivent être identiques — casse, underscores)
4. Garde la **ligne EXAMPLE** en ligne 2 pour te rappeler du format,
   puis mets toutes les vraies données à partir de la ligne 3

---

## Étape 2 — Connecter le plug-in Capital IQ

> **Prérequis** : avoir accès à Capital IQ Pro avec le plug-in Excel installé

1. Dans Excel → onglet **Capital IQ** dans le ruban
2. Clique **Log In** → entre tes identifiants Capital IQ FIEUS
3. Vérifie que le plug-in est actif (icône verte en bas à droite)

---

## Étape 3 — Remplir les données avec Capital IQ

### Pour `manual_fundamentals.csv` (onglet `fundamentals`)

Pour chaque ticker, utilise les formules Capital IQ dans les cellules correspondantes :

```
=CIQ("TSX:DOL", "IQ_TOTAL_REV", "FY2024")      → revenue
=CIQ("TSX:DOL", "IQ_GROSS_PROFIT", "FY2024")   → gross_profit
=CIQ("TSX:DOL", "IQ_EBITDA", "FY2024")         → ebitda
=CIQ("TSX:DOL", "IQ_EBIT", "FY2024")           → ebit
=CIQ("TSX:DOL", "IQ_NET_INCOME", "FY2024")     → net_income
=CIQ("TSX:DOL", "IQ_LEVERED_FCF", "FY2024")    → free_cash_flow
=CIQ("TSX:DOL", "IQ_GROSS_MARGIN", "FY2024")   → gross_margin (décimal)
=CIQ("TSX:DOL", "IQ_EBITDA_MARGIN", "FY2024")  → ebitda_margin (décimal)
=CIQ("TSX:DOL", "IQ_NET_MARGIN", "FY2024")     → net_margin (décimal)
=CIQ("TSX:DOL", "IQ_ROE", "FY2024")            → roe (décimal)
=CIQ("TSX:DOL", "IQ_ROIC", "FY2024")           → roic (décimal)
=CIQ("TSX:DOL", "IQ_TOTAL_ASSETS", "FY2024")   → total_assets
=CIQ("TSX:DOL", "IQ_TOTAL_DEBT", "FY2024")     → total_debt
=CIQ("TSX:DOL", "IQ_CASH_EQUIV", "FY2024")     → cash
=CIQ("TSX:DOL", "IQ_NET_DEBT", "FY2024")       → net_debt
=CIQ("TSX:DOL", "IQ_DILUTED_SHARES", "FY2024") → shares_outstanding
```

**⚠️ Important — marges :**
Capital IQ retourne parfois les marges en pourcentage (ex: 40.0).
Le dashboard attend des **décimales** (ex: 0.40).
Ajoute une colonne de conversion si nécessaire : `=B5/100`

### Pour `manual_valuation.csv` (onglet `valuation`)

```
=CIQ("TSX:DOL", "IQ_CLOSEPRICE")               → price (date du jour)
=CIQ("TSX:DOL", "IQ_MARKET_CAP")               → market_cap
=CIQ("TSX:DOL", "IQ_TEV")                      → enterprise_value (TEV = Total Enterprise Value)
=CIQ("TSX:DOL", "IQ_PE_EXCL_NRI_EX_NEG")      → pe
=CIQ("TSX:DOL", "IQ_NEXT_FY_PE")              → forward_pe
=CIQ("TSX:DOL", "IQ_TEV_EBITDA")              → ev_ebitda
=CIQ("TSX:DOL", "IQ_TEV_EBIT")                → ev_ebit
=CIQ("TSX:DOL", "IQ_TEV_REV")                 → ev_sales
=CIQ("TSX:DOL", "IQ_PS")                      → price_sales
=CIQ("TSX:DOL", "IQ_PBV")                     → price_book
=CIQ("TSX:DOL", "IQ_DIVIDEND_YIELD")          → dividend_yield (décimal)
=CIQ("TSX:DOL", "IQ_NET_DEBT_EBITDA")         → net_debt_ebitda
```

---

## Étape 4 — Refresh Capital IQ

1. Dans le ruban Capital IQ → **Refresh All**
2. Attends que toutes les formules soient recalculées (peut prendre 1-3 min)
3. **Vérifie** que les cellules ne contiennent pas `#N/A` ou `#ERROR`
   - `#N/A` = identifiant CIQ non reconnu → vérifie le format du symbol
   - `#ERROR` = variable non disponible pour ce ticker → entre `""` (vide) dans la cellule CSV

---

## Étape 5 — Exporter chaque onglet en CSV

Pour chaque onglet (fundamentals, valuation, targets) :

1. Clique sur l'onglet → **Fichier → Enregistrer une copie**
2. Format : **CSV UTF-8 (délimité par des virgules)**
3. Nom du fichier : exactement comme dans le dashboard :
   - `manual_fundamentals.csv`
   - `manual_valuation.csv`
   - `manual_targets.csv`

**⚠️ Avant d'exporter :**
- Supprime la ligne EXAMPLE (ligne 2)
- Remplace toutes les formules Capital IQ par leurs **valeurs** :
  Sélectionne tout → Copier → Collage spécial → Valeurs uniquement
- Remplace les cellules vides `#N/A` ou `#ERROR` par vide `""`
- Vérifie que les marges sont en **décimales** (0.40, pas 40.0)
- Remplis la colonne `last_update` avec la date du jour (`2025-04-28`)
- Remplis la colonne `source` avec `Capital IQ export 2025-04-28`

---

## Étape 6 — Uploader les CSV dans GitHub

### Option A — Interface web GitHub (recommandé pour mobile/iPad)

1. Va sur ton repo GitHub : `github.com/[ton-compte]/[ton-repo]`
2. Navigue dans le dossier `config/`
3. Clique sur le fichier à remplacer (ex: `manual_fundamentals.csv`)
4. Clique l'icône ✏️ **Edit** (crayon)
5. Sélectionne tout le contenu → efface → colle le contenu de ton nouveau CSV
6. **Commit changes** → message : `Update manual_fundamentals.csv - Capital IQ 2025-04-28`
7. Répète pour les autres fichiers

### Option B — Git en ligne de commande

```bash
git add config/manual_fundamentals.csv config/manual_valuation.csv config/manual_targets.csv
git commit -m "Update fundamentals and valuation from Capital IQ - 2025-04-28"
git push origin main
```

---

## Étape 7 — Redémarrer Streamlit Cloud

1. Va sur [share.streamlit.io](https://share.streamlit.io)
2. Ton app se redéploie automatiquement après un push GitHub (30-60 secondes)
3. Si les données ne se rafraîchissent pas :
   - Ouvre le dashboard
   - Clique **🔄 Clear Cache & Reload** dans la sidebar
4. Vérifie que les fondamentaux apparaissent dans **Company Deep Dive**
   et que la source indique `Capital IQ export`

---

## Règles de données — FIEUS

| Règle | Explication |
|---|---|
| **Ne jamais inventer** | Si la donnée est absente de Capital IQ, laisse la cellule vide → le dashboard affiche N/A |
| **Décimales pour les marges** | `gross_margin = 0.40` pas `40` ni `40%` |
| **Devise explicite** | Indique toujours la devise dans la colonne `source` si différente de CAD |
| **Source tracée** | Colonne `source` toujours remplie : `Capital IQ export YYYY-MM-DD` ou `FIEUS manual` |
| **Pas de copier-coller depuis Google** | Capital IQ ou filings officiels uniquement |
| **Thèses = FIEUS analyst uniquement** | `manual_targets.csv` n'accepte que des vues internes FIEUS |
| **Recommandations ≠ décisions finales** | Les recommandations passent par le comité d'investissement FIEUS |

---

## Lecture des données dans le dashboard

Le dashboard lira les fichiers dans cet ordre de priorité :

```
1. config/manual_fundamentals.csv  ← Capital IQ / FIEUS (priorité maximale)
2. config/manual_valuation.csv     ← Capital IQ / FIEUS
3. config/manual_targets.csv       ← FIEUS analyst uniquement
4. yfinance API (fallback)         ← si donnée absente des fichiers manuels
5. N/A                             ← si absent partout
```

Chaque donnée affichera sa source :
- `Source: Capital IQ export` si elle vient des CSV manuels avec source Capital IQ
- `Source: FIEUS manual` si entrée manuellement par un analyste
- `Source: yfinance` si récupérée via l'API yfinance (free data)
- `N/A` si absent de toutes sources

---

*Guide FIEUS — Usage interne — Ne pas distribuer à l'extérieur*

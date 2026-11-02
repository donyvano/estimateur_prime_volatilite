# Journal d'apprentissage

| Étape | Mode | Score test | Notions à revoir |
|-------|------|-----------|------------------|
| 0. Cadrage | guidé | 0,5 / 2 (test interrompu après Q2) | call/put vs long/short, $S_T$, maturité, strike |
| 1. Données | autonome | à faire ([quiz](docs/quiz.md#étape-1--données)) | |
| 2. Volatilité réalisée | autonome | à faire | |
| 3. Black-Scholes et Monte Carlo | autonome | à faire | |
| 4. Volatilité implicite | autonome | à faire | |
| 5. Prime de volatilité | autonome | à faire | |
| 6. Prévision | autonome | à faire | |
| 7. Backtest | autonome | à faire | |
| 8. Test final + simulation d'entretien | autonome | à faire ([test final](docs/quiz.md#test-final-15-questions)) | |

À partir de l'étape 1, le projet a été terminé d'une traite, à ma demande. Le plan de révision : pour chaque étape, lire la section du [glossaire](GLOSSARY.md), relire le module de code correspondant, faire le quiz de [docs/quiz.md](docs/quiz.md) **sans regarder les réponses**, puis noter le score ici.

---

## Étape 0 : cadrage

**Ce que j'ai appris :**
- La structure d'un projet reproductible : config unique, package testé, CI, cache des données.
- Une option = un **droit** (pas une obligation) d'acheter (call) ou de vendre (put) un sous-jacent, à un **strike** fixé, jusqu'à une **maturité** donnée, contre une **prime**.

**Mini-test :**
- Q1 (définir une option) : **0,5 / 1**. Il manquait le strike, et « période donnée » était flou à la place de « maturité ».
- Q2 (call vs put) : **0 / 1**. J'ai confondu call/put (le *droit*) avec achat/vente (le *sens*, long/short).
- Q3 (P&L d'un put) : non terminée. J'avais besoin de savoir ce que sont $S_T$ et la maturité.

**Notions ratées, à revoir en priorité :**
1. **Call/put ≠ achat/vente.** On peut acheter ou vendre un call, acheter ou vendre un put : 4 positions (tableau dans [GLOSSARY.md § Long / short](GLOSSARY.md#long--short-acheteur--vendeur)).
2. **Notations :** $S_T$ = prix du sous-jacent à la maturité, $K$ = strike, $T$ = maturité en années ([GLOSSARY.md § 0](GLOSSARY.md#0-notations)).
3. **Payoff vs P&L :** P&L = payoff − prime payée, × 100 actions par contrat.
4. Refaire la Q3 : put $K = 480$, prime 6 $. Réponse : $S_T = 450$ → (30 − 6) × 100 = **+2 400 $** ; $S_T = 500$ → **−600 $**.

---

## Étapes 1 à 8

_À remplir après chaque quiz : score, ce que j'ai compris, ce que je dois revoir._

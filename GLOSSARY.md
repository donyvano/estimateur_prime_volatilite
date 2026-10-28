# Glossaire

Chaque terme : définition simple → formule (si elle existe) → exemple chiffré.
Classement par thème. Mis à jour à chaque étape.

---

## 1. Marchés : les bases

### Action
Une part de propriété d'une entreprise cotée en Bourse. Son prix varie selon l'offre et la demande.
- **Exemple :** une entreprise valorisée 1 milliard € et divisée en 10 millions d'actions → une action vaut 100 €.

### Indice
Un panier d'actions résumé en un seul nombre, pour suivre « le marché ». Le **S&P 500** regroupe 500 grandes entreprises américaines, pondérées par leur capitalisation (les plus grosses pèsent le plus). Un indice ne s'achète pas directement : on passe par un ETF comme **SPY**, qui le réplique.
- **Formule :** $I_t = \dfrac{\sum_i P_{i,t} \times N_i}{D}$ (prix × nombre d'actions, divisé par un « diviseur » $D$ qui neutralise les splits, entrées/sorties, etc.)
- **Exemple :** si une action pèse 5 % de l'indice et monte de 10 %, l'indice monte de 5 % × 10 % = **0,5 %** (toutes choses égales par ailleurs).

### Rendement
La variation relative d'un prix entre deux dates. Deux versions (détaillées à l'étape 1) :
- **Formule simple :** $R_t = \dfrac{P_t}{P_{t-1}} - 1$
- **Formule log :** $r_t = \ln\left(\dfrac{P_t}{P_{t-1}}\right)$
- **Exemple :** le prix passe de 100 à 102 → rendement simple = **2 %**, log-rendement = ln(1,02) ≈ **1,98 %**. Très proches pour de petites variations.

### Volatilité
L'amplitude typique des variations d'un prix : c'est l'**écart-type des rendements**, exprimé par convention **en annuel**. Elle mesure l'agitation, pas la direction.
- **Formule :** $\sigma_{\text{annuelle}} = \sigma_{\text{journalière}} \times \sqrt{252}$ (252 jours de Bourse par an)
- **Exemple :** si le S&P 500 bouge typiquement de 1 % par jour → volatilité ≈ 1 % × √252 ≈ **15,9 %** par an. Sous hypothèse gaussienne, le rendement annuel reste dans ±16 % autour de sa moyenne environ 2 années sur 3.

---

## 2. Options

### Option
Un contrat qui donne le **droit, mais pas l'obligation**, d'acheter ou de vendre un actif (le **sous-jacent**) à un prix fixé d'avance (le **strike**), à une date donnée (la **maturité**). L'acheteur paie ce droit : c'est la **prime**.
- **Européenne :** exercice uniquement à maturité (ex. options sur l'indice SPX, celles qui servent à calculer le VIX).
- **Américaine :** exercice possible à tout moment (ex. options sur SPY). On le gardera en tête à l'étape 4.
- **Exemple :** aux États-Unis, une option sur action porte sur **100 titres**. Une prime cotée 4 $ coûte donc 400 $ par contrat.

### Call
Le droit d'**acheter** le sous-jacent au strike $K$. On l'achète si on pense que le prix va **monter**.
- **Payoff à maturité :** $\max(S_T - K,\ 0)$
- **Exemple :** $K = 100$. Si $S_T = 110$ → payoff = **10**. Si $S_T = 95$ → payoff = **0** (on n'exerce pas).

### Put
Le droit de **vendre** le sous-jacent au strike $K$. Il gagne quand le prix **baisse** : c'est une **assurance** contre la chute.
- **Payoff à maturité :** $\max(K - S_T,\ 0)$
- **Exemple :** $K = 100$. Si $S_T = 90$ → payoff = **10**. Si $S_T = 105$ → payoff = **0**.

### Strike (prix d'exercice)
Le prix $K$, fixé dans le contrat, auquel on peut acheter (call) ou vendre (put).
- **Exemple :** SPY cote 500 $. Un put de strike 450 $ protège contre une baisse de plus de 10 %. Plus le strike est loin du prix actuel, moins l'option a de chances de payer, donc moins elle coûte.

### Maturité (échéance)
La date à laquelle l'option expire. Dans les formules, on l'exprime **en années** : $T$.
- **Exemple :** une option qui expire dans 30 jours calendaires → $T = 30 / 365 \approx$ **0,082 an**. Le VIX mesure justement la volatilité anticipée sur 30 jours.

### Prime (d'une option)
Le **prix de l'option**, payé par l'acheteur au vendeur au départ. C'est la perte maximale de l'acheteur, et le gain maximal du vendeur.
- **Formule (P&L de l'acheteur d'un call à maturité) :** $\max(S_T - K, 0) - \text{prime}$
- **Exemple :** call $K = 100$ acheté 4 $. Si $S_T = 110$ → gain = 10 − 4 = **+6 $**. Si $S_T = 95$ → perte = **−4 $** (la prime). Le vendeur, lui, gagne au plus 4 $ mais peut perdre beaucoup plus : c'est l'asymétrie de la **vente de volatilité** (étape 7).
- ⚠️ **Ne pas confondre** avec la **prime de volatilité (VRP)**, l'écart entre volatilité implicite et volatilité réalisée, qui est le sujet du projet.

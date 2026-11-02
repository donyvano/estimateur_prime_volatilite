# Glossaire

Chaque terme : définition simple → formule (si elle existe) → exemple chiffré.
Classé par thème, dans l'ordre du projet. Les chiffres « projet » viennent des résultats réels (S&P 500, 2005-2026).

**Sommaire :** [0. Notations](#0-notations) · [1. Marchés](#1-marchés--les-bases) · [2. Options](#2-options) · [3. Volatilité réalisée](#3-volatilité-réalisée-étapes-1-2) · [4. Black-Scholes et grecques](#4-black-scholes-et-grecques-étape-3) · [5. Monte Carlo](#5-monte-carlo-étape-3) · [6. Volatilité implicite](#6-volatilité-implicite-et-smile-étape-4) · [7. Prime de volatilité](#7-prime-de-volatilité-étape-5) · [8. Prévision](#8-prévision-étape-6) · [9. Stratégie et risque](#9-stratégie-et-risque-étape-7)

---

## 0. Notations

| Symbole | Se lit | Signification | Exemple |
|---|---|---|---|
| $S_t$ | « S indice t » | prix du sous-jacent à la date $t$ (S pour *spot* / *stock*) | SPY à 755,72 $ le 30/10/2026 |
| $S_0$ | | prix aujourd'hui | |
| $S_T$ | | prix **à la maturité** (le jour où l'option expire) | prix de SPY le 18/12/2026 |
| $K$ | | strike, prix d'exercice fixé dans le contrat | 700 $ |
| $T$ | | maturité **en années** (temps restant avant l'expiration) | 30 jours → $T = 30/365 \approx 0{,}082$ |
| $\sigma$ | « sigma » | volatilité annualisée, en décimal | 0,20 = 20 % |
| $r$ | | taux sans risque continu | 0,04 = 4 % |
| $q$ | | rendement du dividende continu | 0,012 = 1,2 % |
| $F$ | | prix forward : $F = S\,e^{(r-q)T}$ | |
| $N(\cdot)$ | | fonction de répartition de la loi normale | $N(0) = 0{,}5$ |

---

## 1. Marchés : les bases

### Action
Une part de propriété d'une entreprise cotée en Bourse. Son prix varie selon l'offre et la demande.
- **Exemple :** une entreprise valorisée 1 milliard € et divisée en 10 millions d'actions → une action vaut 100 €.

### Indice
Un panier d'actions résumé en un seul nombre, pour suivre « le marché ». Le **S&P 500** regroupe 500 grandes entreprises américaines, pondérées par leur capitalisation. On ne l'achète pas directement : on passe par un ETF comme **SPY**, qui le réplique.
- **Formule :** $I_t = \dfrac{\sum_i P_{i,t} \times N_i}{D}$ ($D$ = diviseur qui neutralise splits, entrées/sorties…)
- **Exemple :** une action qui pèse 5 % de l'indice monte de 10 % → l'indice monte de 0,5 %.

### ETF
Un fonds coté qui réplique un indice. SPY vaut environ 1/10 du S&P 500 (755 $ pour un indice à ~7 550).

### Rendement (simple et log)
La variation relative d'un prix entre deux dates.
- **Simple :** $R_t = P_t / P_{t-1} - 1$ · **Log :** $r_t = \ln(P_t / P_{t-1})$
- **Pourquoi le log :** les log-rendements **s'additionnent** dans le temps ($r_{1\to3} = r_1 + r_2 + r_3$), ce qui simplifie les fenêtres glissantes, et ils sont symétriques (+10 % puis −10 % ne ramène pas à 100, mais $\ln$ le voit).
- **Exemple :** 100 → 102 : simple 2 %, log 1,98 %. Quasi identiques pour de petits mouvements.

### Jours de bourse (252)
Une année compte environ **252 séances** (365 jours − week-ends − ~9 jours fériés). C'est le facteur d'annualisation standard.

### Annualisation
Passer d'une mesure journalière à une mesure annuelle. Une **variance** s'additionne dans le temps (si les jours sont indépendants), donc la **volatilité** croît en racine du temps.
- **Formule :** $\sigma_{\text{an}} = \sigma_{\text{jour}} \times \sqrt{252}$ · $\sigma_{\text{jour}} = \sigma_{\text{an}} / \sqrt{252} \approx \sigma_{\text{an}} / 16$
- **Exemple :** VIX à 20 → le marché anticipe environ 20 / 15,87 ≈ **1,26 %** de mouvement typique par jour.

### Taux sans risque
Le rendement d'un placement sans risque de défaut (bons du Trésor US). On utilise le T-bill 3 mois (^IRX). Projet : 3,97 % au 30/10/2026.

---

## 2. Options

### Option
Un contrat qui donne à son acheteur le **droit, mais pas l'obligation**, d'acheter (call) ou de vendre (put) un **sous-jacent** à un prix fixé d'avance, le **strike** $K$, à une date donnée, la **maturité** $T$. L'acheteur paie ce droit : c'est la **prime**.
- **Européenne :** exercice uniquement à maturité (options sur l'indice SPX, celles du VIX).
- **Américaine :** exercice possible à tout moment jusqu'à maturité (options SPY).
- **Exemple :** aux États-Unis, 1 contrat = 100 titres. Une prime cotée 4 $ coûte 400 $.

### Call
Le droit d'**acheter** au strike $K$. Il gagne quand le marché **monte**.
- **Payoff à maturité :** $\max(S_T - K,\ 0)$
- **Exemple :** $K = 100$ ; $S_T = 110$ → 10 ; $S_T = 95$ → 0.

### Put
Le droit de **vendre** au strike $K$. Il gagne quand le marché **baisse** : c'est une **assurance**.
- **Payoff à maturité :** $\max(K - S_T,\ 0)$
- **Exemple :** $K = 480$, prime 6 $. $S_T = 450$ → payoff 30, P&L = (30 − 6) × 100 = **+2 400 $** par contrat. $S_T = 500$ → payoff 0, P&L = **−600 $**.

### Long / short (acheteur / vendeur)
⚠️ **À ne pas confondre avec call / put.** Call/put = *quel droit* ; long/short = *qui paie la prime*.

|  | Call | Put |
|---|---|---|
| **Long (acheteur)** | parie sur la hausse, perte max = prime | s'assure contre la baisse, perte max = prime |
| **Short (vendeur)** | encaisse la prime, perte potentiellement illimitée | encaisse la prime, grosse perte en cas de krach |

Mnémotechnique : **Call** → tu *appelles* l'actif à toi (achat). **Put** → tu le *poses* chez un autre (vente).

### Strike (prix d'exercice)
Le prix $K$ fixé dans le contrat. Plus il est loin du prix actuel, moins l'option a de chances de payer, donc moins elle coûte.
- **Exemple :** SPY à 755 $. Un put strike 680 $ (−10 %) protège contre une chute de plus de 10 %.

### Maturité (échéance)
La date d'expiration du contrat. Comme une assurance auto valable jusqu'au 31 décembre. On l'exprime en années : $T$.
- **Exemple :** option qui expire dans 30 jours → $T \approx 0{,}082$.

### Prime (d'une option)
Le **prix** de l'option, payé par l'acheteur au vendeur au départ. C'est la perte maximale de l'acheteur, et le gain maximal du vendeur.
- ⚠️ À ne pas confondre avec la **prime de volatilité** (VRP), le sujet du projet (§7).

### Moneyness
Où se situe le strike par rapport au prix. On utilise $K/F$ (strike / forward) ou $\ln(K/F)$.
- **ATM** (à la monnaie) : $K \approx F$. **ITM** (dans la monnaie) : l'option aurait une valeur si on l'exerçait maintenant. **OTM** (hors de la monnaie) : elle n'en aurait pas.
- **Exemple :** put $K/F = 0{,}90$ = put OTM, protège contre −10 %.

### Valeur intrinsèque / valeur temps
Prix d'une option = **valeur intrinsèque** (ce qu'elle rapporterait exercée tout de suite) + **valeur temps** (la chance que ça s'améliore d'ici la maturité).
- **Exemple :** call $K = 100$, $S = 105$, prix 8 → intrinsèque 5, valeur temps 3.

### Parité call-put
Relation sans arbitrage entre call et put de même strike et maturité (européennes) :
- **Formule :** $C - P = S e^{-qT} - K e^{-rT} = e^{-rT}(F - K)$
- **Usage projet :** on en déduit le **forward implicite** $F$ de chaque échéance, donc les dividendes, sans les deviner. Le test `test_put_call_parity` la vérifie à $10^{-10}$ près.

### Forward
Prix d'achat à terme, fixé aujourd'hui pour livraison en $T$ : $F = S e^{(r-q)T}$. Il intègre le coût de portage (taux − dividendes).
- **Exemple projet :** SPY 755,72 $, échéance 18/12/2026 → $F \approx 759{,}3$ $.

---

## 3. Volatilité réalisée (étapes 1-2)

### Volatilité
L'amplitude typique des variations d'un prix : l'**écart-type des rendements**, exprimé en annuel. Elle mesure l'agitation, pas la direction.
- **Exemple :** 1 % par jour → ≈ 15,9 % par an.

### Volatilité réalisée (close-to-close)
La volatilité **mesurée** sur les rendements passés, à partir des clôtures.
- **Formule (projet, convention variance swap) :** $\sigma_t = \sqrt{\dfrac{252}{n}\sum_{i=t-n+1}^{t} r_i^2}$ avec $n = 21$
- On ne retire pas la moyenne : sur 21 jours elle est négligeable (~0,03 %/jour) et très bruitée. C'est aussi la définition du payoff d'un variance swap.
- **Projet :** médiane 12,8 %, maximum 96 % (6 avril 2020).

### Estimateur de Parkinson
Volatilité estimée à partir des **plus hauts et plus bas** du jour : l'amplitude intraday contient plus d'information qu'une seule clôture.
- **Formule :** $\sigma^2 = \dfrac{252}{4\ln 2} \cdot \dfrac{1}{n}\sum \ln(H_i/L_i)^2$
- ~5× plus efficace en théorie, mais **biaisé vers le bas** : il ignore les gaps de nuit (ouverture ≠ clôture de la veille).
- **Projet :** Parkinson ≈ 0,82 × close-to-close en médiane.

### Clustering de volatilité
Les jours agités suivent les jours agités. La volatilité est **persistante**, donc partiellement prévisible.
- **Projet :** corrélation de 0,66 entre la vol d'aujourd'hui et celle d'il y a 21 jours.

### Régime de marché
Période où le marché a un comportement stable : régime calme (vol ~10-12 %) ou régime de stress (vol > 30 %). Les transitions sont brutales.

### Effet de levier
La volatilité monte davantage après une **baisse** qu'après une hausse de même taille (asymétrie). Une des raisons du skew.

---

## 4. Black-Scholes et grecques (étape 3)

### Modèle de Black-Scholes
Modèle de prix d'option (1973). **Hypothèses :** le prix suit un mouvement brownien géométrique, la volatilité et les taux sont constants, pas de coûts de transaction, échange en continu, pas d'arbitrage.
- **Formules :** $d_1 = \dfrac{\ln(S/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$, $d_2 = d_1 - \sigma\sqrt{T}$
  - $C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)$
  - $P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)$
- **Exemple (Hull) :** $S = K = 100$, $T = 1$, $r = 5\,\%$, $\sigma = 20\,\%$ → call **10,45**, put **5,57**.

### Prix risque-neutre
Le prix d'une option = espérance de son payoff **actualisée**, calculée dans un monde fictif où tous les actifs rapportent le taux sans risque. On n'a pas besoin de connaître le rendement attendu de l'action : on peut répliquer l'option en couvrant (delta-hedging).

### Mouvement brownien géométrique (GBM)
$dS = \mu S\,dt + \sigma S\,dW$ : le **log-prix** suit une marche aléatoire gaussienne. Solution exacte : $S_T = S_0 \exp\big((r - q - \sigma^2/2)T + \sigma\sqrt{T}Z\big)$, $Z \sim N(0,1)$.

### Delta (Δ)
**Trader :** « de combien bouge mon option si le sous-jacent bouge de 1 $ » ; aussi le nombre d'actions pour se couvrir.
- Call ∈ [0, 1], put ∈ [−1, 0]. ATM ≈ 0,5.
- **Exemple :** delta 0,64 → si SPY monte de 1 $, le call gagne ~0,64 $.

### Gamma (Γ)
**Trader :** « à quelle vitesse mon delta change » ; ma convexité. Toujours positif pour l'acheteur, maximal ATM près de la maturité. Le vendeur d'options est **short gamma** : il souffre des gros mouvements.

### Vega (ν)
**Trader :** « combien je gagne si la volatilité implicite monte de 1 point ». Toujours positif pour l'acheteur.
- **Exemple :** vega 37,5 (pour 1,00 de vol) → +0,375 $ par point de vol.

### Theta (Θ)
**Trader :** « combien je perds chaque jour qui passe, toutes choses égales ». Négatif pour l'acheteur : c'est le loyer de l'assurance. Le vendeur d'options encaisse le theta et paie le gamma.
- **Exemple :** theta −6,41 par an → ≈ −0,018 $ par jour (÷ 365).

---

## 5. Monte Carlo (étape 3)

### Méthode de Monte Carlo
Estimer une espérance en **simulant** beaucoup de scénarios et en faisant la moyenne. Pour une option : simuler $N$ prix $S_T$, calculer les payoffs, moyenner, actualiser.
- Lien direct avec le cours de Monte Carlo à l'EFREI : même estimateur de moyenne empirique, même TCL.

### Convergence en $1/\sqrt{N}$
Par le théorème central limite, l'erreur standard vaut $\sigma_{\text{payoff}} / \sqrt{N}$ : **4 fois plus de trajectoires = erreur 2 fois plus petite**.
- **Projet :** call ATM 1 mois, 100 trajectoires → erreur 3,8 $ ; 300 000 → 0,002 $.

### Variables antithétiques
Technique de réduction de variance : on simule $Z$ et $-Z$ en paires. Les erreurs se compensent en partie → erreur plus faible à $N$ égal.

---

## 6. Volatilité implicite et smile (étape 4)

### Volatilité implicite
La volatilité $\sigma$ qui, mise dans Black-Scholes, redonne **le prix observé sur le marché**. C'est la vol que le marché « paie », pas une mesure du passé.
- **Exemple projet :** call SPY ATM 1 mois → vol implicite ≈ **15,8 %**.

### Inversion (Newton-Raphson + Brent)
Black-Scholes est croissant en $\sigma$ (vega > 0), donc l'inverse existe.
- **Newton :** $\sigma_{n+1} = \sigma_n - \dfrac{BS(\sigma_n) - \text{prix}}{\text{vega}(\sigma_n)}$, convergence quadratique près de l'ATM.
- **Repli Brent :** quand la vega est quasi nulle (options très OTM ou courtes), Newton diverge ; Brent encadre la racine et converge toujours.

### VIX
Indice de volatilité implicite à **30 jours** du S&P 500, calculé par le CBOE à partir d'un **panier d'options SPX de tous les strikes**. C'est la racine du prix d'un variance swap 30 jours.
- **Projet :** moyenne 2005-2026 = **19,1 %** ; 19,4 % le 30/10/2026.

### Smile / skew
La vol implicite n'est **pas constante** selon le strike (Black-Scholes supposait que si). Sur les actions, elle est plus haute pour les strikes bas : c'est un **skew** (smile penché).
- **Pourquoi :** demande massive de puts de protection, krachs plus brutaux que les hausses, effet de levier.
- **Projet :** put 90 % à **27,1 %** contre call 110 % à **12,4 %** (1 mois), soit 14,7 points d'écart.

### Structure par terme
Vol implicite ATM selon la **maturité**. En temps calme elle monte avec la maturité (contango) ; en crise elle s'inverse (le court terme fait peur).
- **Projet :** 16,1 % à 21 jours → 17,4 % à 322 jours.

### Surface de volatilité
La vol implicite en fonction du strike **et** de la maturité. C'est l'objet qu'un desk d'options calibre chaque jour.

---

## 7. Prime de volatilité (étape 5)

### Prime de volatilité (VRP, Volatility Risk Premium)
L'écart entre la volatilité **anticipée** (implicite) et la volatilité **réalisée ensuite**.
- **Formule :** $VRP_t = VIX_t - RV_{t+1 \to t+21}$
- **Analogie :** prix de l'assurance moins sinistres payés. L'assureur gagne en moyenne, mais une catastrophe coûte cher.
- **Projet :** moyenne **+3,5 points**, médiane +4,3, positive **84 %** des jours, pire **−72 points** (20 février 2020).

### Biais de look-ahead (anticipation)
Utiliser, à la date $t$, une information qui n'était pas connue à la clôture de $t$. C'est la triche la plus fréquente en backtest.
- **Exemple :** la vol réalisée de $t+1$ à $t+21$ n'est connue qu'en $t+21$. Elle sert de **cible**, jamais de variable explicative.
- **Projet :** tests qui modifient le futur et vérifient que rien ne change avant $t$.

### Risque de queue
Risque d'événements extrêmes et rares (krachs) que la loi normale sous-estime. Le vendeur de volatilité y est très exposé.

---

## 8. Prévision (étape 6)

### Modèle naïf
« La vol des 21 prochains jours = celle des 21 derniers. » La référence à battre.

### HAR-RV (Corsi, 2009)
Régression linéaire de la variance future sur les variances passées à 1 jour, 5 jours et 22 jours.
- **Formule :** $RV^2_{t+1\to t+21} = \beta_0 + \beta_d RV^2_{d} + \beta_w RV^2_{w} + \beta_m RV^2_{m}$
- **Intuition :** des acteurs à horizons différents (traders intraday, gérants hebdo, institutionnels mensuels).
- **HAR-X :** on ajoute VIX² comme régresseur. **Meilleur modèle du projet** : RMSE −13,8 % vs naïf.

### GARCH(1,1)
Modèle où la variance de demain dépend du choc d'aujourd'hui et de la variance d'aujourd'hui.
- **Formule :** $\sigma^2_{t+1} = \omega + \alpha r_t^2 + \beta \sigma^2_t$ ; $\alpha + \beta$ proche de 1 = forte persistance.

### LightGBM
Gradient boosting d'arbres de décision. Capte des non-linéarités. **Projet :** meilleure MAE, mais sous-estime les chocs (QLIKE moins bon). Variable n°1 : le VIX.

### Walk-forward (validation)
Entraîner sur le passé, tester sur l'année suivante, avancer d'un an, recommencer. **Jamais de split aléatoire** sur une série temporelle : il mélange passé et futur, et la persistance de la vol fait « fuiter » l'information.

### Purge
Retirer de l'entraînement les dernières observations dont la **cible** déborde sur la période de test (ici 21 jours).

### RMSE / MAE
Racine de l'erreur quadratique moyenne / erreur absolue moyenne, en points de vol. La RMSE pénalise plus les grosses erreurs.

### QLIKE
Fonction de perte robuste pour prévoir une variance : $\text{QLIKE} = \dfrac{RV^2}{h} - \ln\dfrac{RV^2}{h} - 1$. Vaut 0 si la prévision est parfaite, et **pénalise plus la sous-estimation** que la surestimation : c'est ce que veut un risk manager.

### Correction de Duan (smearing)
Quand on modélise $\ln(y)$, $e^{\hat{E}[\ln y]}$ sous-estime $E[y]$ (inégalité de Jensen). On multiplie par la moyenne de $e^{\text{résidus}}$ calculée sur l'entraînement.

---

## 9. Stratégie et risque (étape 7)

### Variance swap
Contrat qui échange la **variance réalisée** contre un **strike de variance** fixé au départ. L'acheteur reçoit $N_{var}(RV^2 - K^2)$.
- **Vendre un variance swap = vendre de la volatilité** : on encaisse $K^2$, on paie la variance réalisée.
- **P&L vendeur (par unité de vega) :** $\dfrac{K^2 - RV^2}{2K}$ ≈ $K - RV$ quand $RV$ est proche de $K$, mais convexe : les pertes explosent avec $RV^2$.
- **Exemple :** $K = 20$, $RV = 15$ → +4,4 pts ; $RV = 30$ → −12,5 pts ; $RV = 40$ → −30 pts.
- **Plafond (cap) :** en pratique, $RV$ est plafonnée à 2,5 × $K$.

### Vega notional
Montant gagné ou perdu par point de volatilité. Projet : 0,5 % du capital par point de vol.

### Ratio de Sharpe
Rendement excédentaire moyen / volatilité, annualisé : $\text{Sharpe} = \dfrac{\bar{r}}{\sigma_r}\sqrt{12}$ (données mensuelles).
- ⚠️ **Il ne voit pas les queues** : une stratégie qui gagne 1 % par mois puis perd 30 % un mois a un Sharpe trompeur.
- **Projet :** « toujours vendre » Sharpe 0,76 mais skew −4,5 et pire mois −32 %.

### Drawdown maximal
La plus forte chute depuis un plus haut historique. **Projet :** −46 % en vendant toujours, −19 % en conditionnel HAR-X.

### Skewness (asymétrie) / kurtosis
**Skew négatif** : beaucoup de petits gains, quelques très grosses pertes. **Kurtosis élevée** : queues épaisses (événements extrêmes plus fréquents qu'une loi normale).

### CVaR 5 % (Expected Shortfall)
La perte moyenne dans les 5 % pires cas. Plus informative que la VaR, qui ne donne que le seuil.

### Coûts de transaction
Écart bid-ask et frais. Projet : 0,5 point de vol par transaction.

### Data snooping
Ajuster les paramètres (seuil, modèle) en regardant les résultats du test : la performance devient trop belle. **Projet :** seuil fixé a priori, sensibilité affichée, pas optimisée.

### Sensibilité à la date de roll
Avec des trades mensuels, le résultat dépend du jour du mois où l'on renouvelle le contrat. **Projet :** Sharpe HAR-X entre 0,36 et 1,71 selon la date. On rapporte la distribution, pas le meilleur cas.

### Volmageddon
Le 5 février 2018, le VIX a doublé en une journée (+116 %), détruisant les produits qui vendaient la volatilité (XIV a perdu ~95 % et fermé).

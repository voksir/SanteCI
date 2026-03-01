# 🤖 PROMPT CURSOR — Implémentation Fuzzy Search · Sante CI

---

## 🎯 Contexte & Objectif

Tu es un agent expert React/TypeScript travaillant sur le projet **Sante CI** — une SPA
médicale ivoirienne construite avec **React 18, TypeScript, Vite, TanStack Query,
Tailwind CSS et shadcn-ui**.

Le projet souffre d'un **problème critique de recherche** : la recherche actuelle est
une correspondance exacte sur sous-chaîne (`includes` / `startsWith`). Résultat : un
utilisateur qui tape `"eferalgan"` au lieu de `"EFFERALGAN"` obtient **0 résultat**
alors que l'intention est parfaitement claire. Ce problème touche à la fois la
**recherche de médicaments** et la **recherche de pharmacies**.

L'objectif de cette session est de :
1. **Analyser le workspace** pour comprendre la structure réelle du projet
2. **Identifier tous les endroits** où une recherche est actuellement implémentée
3. **Proposer un plan d'implémentation structuré** du fuzzy search avant toute écriture de code

---

## 📋 Phase 1 — Analyse du workspace (NE PAS ÉCRIRE DE CODE)

Avant tout, explore le projet et réponds à ces questions précises :

### 1.1 Structure des fichiers
- Lire `src/pages/` → lister toutes les pages qui contiennent un champ de recherche
- Lire `src/components/` → identifier les composants de recherche existants
- Lire `src/lib/` → vérifier si un utilitaire de recherche existe déjà
- Lire `src/types/` ou tout fichier de types → identifier les interfaces `Medication`,
  `Pharmacy` et tous leurs champs réels

### 1.2 Logique de recherche actuelle
Pour chaque page identifiée avec une recherche, répondre à :
- Quel est l'état local qui stocke le query ? (`useState`, `useSearchParams`, autre ?)
- Comment le filtre est-il appliqué ? (`filter + includes` ? `filter + toLowerCase` ?)
- Les données viennent-elles d'un `useQuery` TanStack Query, d'un état local, ou
  d'un fichier statique ?
- Quel est le nom exact de la variable qui contient la liste filtrée ?

### 1.3 Types de données réels
- Lister **tous les champs** de l'interface `Medication` telle qu'elle existe dans le
  projet (pas les champs supposés — les champs réels)
- Lister **tous les champs** de l'interface `Pharmacy` telle qu'elle existe dans le
  projet
- Y a-t-il d'autres entités searchables (cliniques, médecins, assurances...) ?

### 1.4 Infrastructure existante
- Vérifier si `fuse.js` est déjà dans `package.json`
- Vérifier la version de `@tanstack/react-query` installée (v4 ou v5 — l'API diffère)
- Vérifier si un alias `@/` est configuré dans `vite.config.ts`
- Vérifier si des tests Vitest existent déjà dans `src/test/`

---

## 📐 Phase 2 — Architecture à implémenter

Voici l'architecture cible à analyser et adapter à ton workspace :

### Structure de fichiers à créer
```
src/
  lib/
    fuzzy/
      index.ts              ← point d'entrée public (exports)
      types.ts              ← interfaces FuzzyResult, UseFuzzySearchOptions
      fuse-config.ts        ← clés de recherche et thresholds par domaine
      use-fuzzy-search.ts   ← hook principal avec debounce intégré
      highlight.ts          ← utilitaire calcul des segments surlignés

  components/
    search/
      SearchInput.tsx       ← input réutilisable avec spinner + bouton clear
      SearchHighlight.tsx   ← rendu texte avec portions matchées surlignées
      FuzzySearchBadge.tsx  ← badge ambré "Résultats approchants"

  test/
    fuzzy-search.test.ts    ← tests Vitest
```

### Dépendance à installer
```bash
npm install fuse.js
```

### Librairie choisie : Fuse.js
- Recherche floue (fuzzy) côté client, zéro dépendance serveur
- Options clés à utiliser :
  - `includeScore: true` → classer par pertinence
  - `includeMatches: true` → données pour le highlight
  - `ignoreDiacritics: true` → "paracetamol" trouve "paracétamol"
  - `ignoreLocation: true` → position du mot dans le champ sans importance
  - `minMatchCharLength: 2` → éviter les faux positifs sur 1 caractère
  - `shouldSort: true` → résultats triés par score automatiquement

### Thresholds recommandés
- Médicaments : `0.30` (plus strict — enjeu sécurité)
- Pharmacies : `0.35` (légèrement plus permissif)

### Clés de recherche et poids — Médicaments
Adapter ces poids aux champs **réels** trouvés dans le workspace :
```
name             → weight 0.35   (nom commercial)
brand_name       → weight 0.25   (marque)
generic_name     → weight 0.20   (DCI)
active_ingredient→ weight 0.10   (principe actif)
group            → weight 0.05   (groupe thérapeutique)
strength         → weight 0.03   (dosage)
code             → weight 0.02   (code produit)
```
⚠️ Si certains champs n'existent pas dans le type réel, les **supprimer** de la config.

### Clés de recherche et poids — Pharmacies
```
display_name → weight 0.40
name         → weight 0.30
city         → weight 0.15
area         → weight 0.10
address      → weight 0.03
phones       → weight 0.02
```
⚠️ Même règle : adapter aux champs réels uniquement.

### Hook principal `useFuzzySearch`
Le hook doit retourner :
```typescript
{
  results: T[]           // liste filtrée — remplace la liste actuelle
  fuzzyResults: FuzzyResult<T>[]  // avec score et matches pour highlight
  isSearching: boolean   // true pendant le debounce → spinner dans SearchInput
  isFuzzyMode: boolean   // true si au moins un résultat est approximatif → badge
  debouncedQuery: string // query après délai → affichage dans le compteur
}
```
Le debounce par défaut est **200ms** — évite de recalculer Fuse à chaque frappe.
L'index Fuse doit être **mémoïsé sur `items`** uniquement via `useMemo`.

---

## 🗺️ Phase 3 — Plan d'implémentation à produire

Sur la base de l'analyse (Phase 1) et de l'architecture (Phase 2), produire un plan
d'implémentation **ordonné et numéroté** sous ce format exact :

```
ÉTAPE 1 — Installation
  Action : npm install fuse.js
  Fichier modifié : package.json

ÉTAPE 2 — Création du module lib/fuzzy/
  Fichiers à créer (dans l'ordre) :
    - src/lib/fuzzy/types.ts        → interfaces adaptées aux types réels du projet
    - src/lib/fuzzy/fuse-config.ts  → clés et poids adaptés aux champs réels
    - src/lib/fuzzy/use-fuzzy-search.ts → hook avec debounce
    - src/lib/fuzzy/highlight.ts    → utilitaire segments
    - src/lib/fuzzy/index.ts        → exports

ÉTAPE 3 — Création des composants search/
  Fichiers à créer :
    - src/components/search/SearchInput.tsx
    - src/components/search/SearchHighlight.tsx
    - src/components/search/FuzzySearchBadge.tsx

ÉTAPE 4 — Migration page [NOM RÉEL DE LA PAGE MÉDICAMENTS]
  Fichier modifié : src/pages/[NomRéel].tsx
  Changements :
    - Remplacer [variable actuelle] par useFuzzySearch(...)
    - Remplacer <input> par <SearchInput>
    - Ajouter <FuzzySearchBadge visible={isFuzzyMode} />
    - Ajouter <SearchHighlight> dans la carte médicament
    - Adapter le compteur pour afficher debouncedQuery

ÉTAPE 5 — Migration page [NOM RÉEL DE LA PAGE PHARMACIES]
  [même structure]

ÉTAPE 6 — Tests
  Fichier à créer : src/test/fuzzy-search.test.ts
  Cas couverts :
    - "eferalgan" trouve EFFERALGAN
    - "amoxiline" trouve AMOXICILLINE
    - recherche sans accent trouve avec accent
    - query vide retourne toute la liste
    - [autres cas spécifiques aux données réelles]

ÉTAPE 7 — Vérification
  Commandes : npm test && npm run lint
```

---

## ⚠️ Règles importantes pour l'agent

1. **Ne pas écrire de code avant d'avoir terminé la Phase 1** — le plan doit être basé
   sur les fichiers réels du workspace, pas sur des suppositions.

2. **Adapter les types aux interfaces réelles** — si `Medication` dans le projet
   s'appelle `Drug` ou `IMedication`, utiliser ce nom.

3. **Préserver la logique existante** — le fuzzy search vient en **remplacement** du
   filtre actuel, pas en couche supplémentaire. Supprimer l'ancien `filter + includes`.

4. **Respecter les conventions du projet** — si les composants utilisent `export
   default`, faire pareil. Si le projet utilise des barrel exports (`index.ts`), les
   maintenir.

5. **Compatible TanStack Query v4 et v5** — vérifier la version et adapter
   (`cacheTime` en v4 devient `gcTime` en v5).

6. **Un seul `useFuzzySearch` pour tout** — le même hook générique `<T>` sert pour
   les médicaments, les pharmacies, et tout autre domaine futur.

7. **Ne pas toucher aux fichiers `shadcn-ui/ui/`** — utiliser les composants existants
   (`Input`, `Badge`...) comme base, ne pas les modifier.

---

## ✅ Livrable attendu de cette session

À la fin, l'agent doit produire :

- [ ] Un **rapport d'analyse** : liste des pages concernées, noms des variables de
      recherche actuelles, champs réels des types
- [ ] Un **plan d'implémentation** complet et ordonné (format ci-dessus)
- [ ] Une **liste des questions bloquantes** s'il manque des informations
- [ ] La confirmation que **fuse.js n'est pas encore installé** (ou qu'il l'est déjà)

**Ne pas commencer l'écriture du code tant que le plan n'est pas validé.**

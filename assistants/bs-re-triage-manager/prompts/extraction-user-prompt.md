# Extraction Complète des Données de Conversation

Extrayez **TOUTES** les informations de cette conversation immobilière en suivant rigoureusement le schéma JSON.

## Checklist d'extraction obligatoire:

### 1. Informations Client (customer_info)
- [ ] **validated_phone** (CRITIQUE): Format XXX-XXX-XXXX validé explicitement
- [ ] **first_name**: Prénom du client
- [ ] **last_name**: Nom de famille
- [ ] **email**: Adresse courriel si fournie
- [ ] **customer_known**: Le client était-il déjà dans la base de données?
- [ ] **customer_title**: Monsieur/Madame si mentionné

### 2. Classification de l'Appel (call_type)
- [ ] Type principal: property_inquiry_specific, property_inquiry_beginner, appointment_booking, etc.

### 3. Étape du Parcours Client (customer_status)
- [ ] Position dans le parcours: first_time_buyer, beginner_buyer, informed_buyer, etc.

### 4. Routage des Transferts (transfer_info)
- [ ] **transferred_to**: Vers quel assistant/manager
- [ ] **transfer_reason**: Raison explicite du transfert
- [ ] **silent_transfer**: Était-ce silencieux (true/false)?

### 5. Détails Immobiliers (property_details)
- [ ] **property_address**: Adresse complète si discutée
- [ ] **property_type**: Type de propriété (maison, condo, etc.)
- [ ] **mls_number**: Numéro MLS si mentionné
- [ ] **price_range**: {min: X, max: Y} en CAD
- [ ] **bedrooms**: Nombre de chambres
- [ ] **bathrooms**: Nombre de salles de bain
- [ ] **search_sector**: Zone/quartier de recherche
- [ ] **property_features**: Liste des caractéristiques souhaitées

### 6. Rendez-vous (appointment_details)
- [ ] **appointment_type**: Type de rendez-vous
- [ ] **appointment_date**: Format YYYY-MM-DD
- [ ] **appointment_time**: Format HH:MM (24h)
- [ ] **appointment_status**: scheduled, modified, cancelled, pending
- [ ] **appointment_id**: ID système si créé

### 7. Analyse de Sentiment (sentiment_analysis)
- [ ] **overall_sentiment**: very_positive, positive, neutral, negative, frustrated
- [ ] **urgency_level**: immediate, high, medium, low, browsing
- [ ] **readiness_to_act**: ready_to_buy, actively_searching, exploring_options, etc.
- [ ] **hesitation_factors**: Liste des préoccupations

### 8. Scoring du Lead (lead_quality)
- [ ] **score**: hot, warm, cool, cold
- [ ] **scoring_factors**: Facteurs justifiant le score
- [ ] **timeline**: Timeline anticipée pour l'action

### 9. Pitch Découverte pour Débutants (discovery_pitch)
- [ ] **pitch_made**: Le pitch a-t-il été fait? (true/false)
- [ ] **customer_response**: Réponse du client au pitch
- [ ] **discovery_scheduled**: Appel découverte planifié? (true/false)

### 10. Messages et Suivi (message_info)
- [ ] **message_taken**: Message pris pour le courtier? (true/false)
- [ ] **message_content**: Contenu du message
- [ ] **callback_requested**: Rappel demandé? (true/false)
- [ ] **preferred_callback_time**: Heure préférée pour le rappel

### 11. Actions Système (system_actions)
- [ ] **tools_triggered**: Liste des outils/fonctions appelés
- [ ] **customer_created**: Nouveau client créé? (true/false)
- [ ] **customer_updated**: Client existant mis à jour? (true/false)
- [ ] **calendar_checked**: Disponibilité vérifiée? (true/false)

### 12. Métadonnées (call_metadata)
- [ ] **call_source**: phone_call, web_call, unknown
- [ ] **call_duration**: Durée en secondes
- [ ] **assistant_path**: Séquence des assistants (ex: ['Alex', 'Sophie', 'Alex'])
- [ ] **language**: french ou english

### 13. Validation des Données (data_validation)
- [ ] **phone_validated**: Téléphone validé explicitement? (true/false)
- [ ] **address_confirmed**: Adresse confirmée? (true/false)
- [ ] **appointment_confirmed**: Rendez-vous confirmé? (true/false)

### 14. Actions de Suivi (follow_up_actions & follow_up_required)
- [ ] **follow_up_required**: Suivi nécessaire? (true/false)
- [ ] **follow_up_actions**: Liste des actions avec type, priorité et notes

### 15. Résultat de l'Appel (call_outcome)
- [ ] Résultat final: appointment_booked, information_provided, transferred_successfully, etc.

### 16. Notes Additionnelles (notes)
- [ ] Observations importantes ou détails critiques de la conversation

## IMPORTANT
- Retournez un JSON valide correspondant EXACTEMENT au schéma
- Utilisez `null` pour toute valeur manquante ou non mentionnée
- N'inventez JAMAIS de données - extrayez uniquement ce qui est explicite dans la conversation

**Conversation à analyser:**
{{transcript}}
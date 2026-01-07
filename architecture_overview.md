# QuickEats V2 System Architecture

This document provides a visual overview of the refactored QuickEats V2 API architecture, focusing on the new patterns implemented: Action-oriented Resources, Optimistic Locking, Idempotency, and Side-loading.

## 1. Database Schema (ER Diagram)

The `Order` model is the central entity, now linked to `Restaurant` and `Rider` to solve the N+1 problem. `IdempotencyKey` ensures safe retries.

```mermaid
erDiagram
    ORDER {
        int id PK
        string status "Enum (payment, acceptance, etc.)"
        int version "Optimistic Locking"
        datetime created_at
        int restaurant_id FK
        int rider_id FK
    }

    RESTAURANT {
        int id PK
        string name
        string address
    }

    RIDER {
        int id PK
        string name
    }

    IDEMPOTENCY_KEY {
        uuid key PK
        int response_status
        json response_body
        datetime created_at
    }

    RESTAURANT ||--o{ ORDER : "receives"
    RIDER ||--o{ ORDER : "delivers"
```

## 2. Request Processing Flow (Pipeline)

Every V2 POST request goes through the following pipeline. This ensures both **Consistency** (Optimistic Locking) and **Reliability** (Idempotency).

```mermaid
flowchart TD
    Client[Client Request] --> A{Idempotency Key?}
    
    %% Idempotency Layer
    A -- Yes --> B{Key Exists?}
    B -- Yes --> C[Return Cached Response]
    B -- No --> D[Proceed to View]
    A -- No --> D
    
    %% Optimistic Locking Layer
    D --> E{Action Endpoint?}
    E -- Yes --> F{If-Match Header?}
    F -- Exists --> G{ETag == Current?}
    G -- Match --> H[Execute Business Logic]
    G -- Mismatch --> I[412 Precondition Failed]
    F -- Missing --> J[400 Bad Request]
    
    %% Execution
    H --> K[Update State & Increment Version]
    K --> L[Save to DB]
    L --> M{Idempotency Key?}
    M -- Yes --> N[Cache Response]
    M -- No --> O[Return Response]
    N --> O
```

## 3. Order State Machine (V2 Lifecycle)

The V2 API enforces strict state transitions via explicit Action Endpoints.

```mermaid
stateDiagram-v2
    [*] --> PENDING_PAYMENT
    
    PENDING_PAYMENT --> PENDING_ACCEPTANCE : POST /payment
    PENDING_PAYMENT --> CANCELLED : POST /cancellation
    
    PENDING_ACCEPTANCE --> PREPARING : POST /acceptance
    PENDING_ACCEPTANCE --> REJECTED : POST /rejection
    PENDING_ACCEPTANCE --> CANCELLED : POST /cancellation
    
    PREPARING --> READY_FOR_PICKUP : POST /preparation-complete
    
    READY_FOR_PICKUP --> IN_TRANSIT : POST /pickup
    
    IN_TRANSIT --> DELIVERED : POST /delivery
    
    CANCELLED --> [*]
    REJECTED --> [*]
    DELIVERED --> [*]
```

## 4. N+1 Problem Solution (Side-loading)

The `list` endpoint optimizes data fetching using `select_related` and returns a compound document.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database

    Client->>API: GET /orders/?include=restaurant,rider
    
    Note over API: Parse ?include params
    
    API->>Database: SELECT * FROM Order <br/> LEFT JOIN Restaurant <br/> LEFT JOIN Rider
    Note right of Database: Single Query (O(1))
    
    Database-->>API: Result Set (Orders + Related Data)
    
    API->>API: Construct "included" dictionary
    
    API-->>Client: JSON Response { results: [...], included: {...} }
```

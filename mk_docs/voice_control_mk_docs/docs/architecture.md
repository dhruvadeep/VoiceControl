# System Architecture
```mermaid
graph LR;
    UI[Client UI] -->|Recording| Transcriber;
    Transcriber -->|Commands| UI;
    UI -->|Commands| Aggregator;

    subgraph System
        Aggregator -->|Browser Commands| BrowserAPI;
        Aggregator -->|Hardware Commands| HardwareAPI;
    end
```

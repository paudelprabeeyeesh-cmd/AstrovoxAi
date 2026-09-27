# AstrovoxAI Java SDK

Official Java SDK for AstrovoxAI.

## Installation

```xml
<dependency>
  <groupId>ai.astrovox</groupId>
  <artifactId>astrovox-sdk</artifactId>
  <version>1.0.0</version>
</dependency>
```

## Quick Start

```java
import ai.astrovox.AstrovoxClient;

AstrovoxClient client = new AstrovoxClient("avx_...");
String response = client.sendMessage("conv_123", "Hello, Astrovox!");
System.out.println(response);
```

See [sdk/java/](../sdk/java/) for the full source code and [Java SDK Guide](/sdk/java) for documentation.

# Recette : nœud MARI NoCluster + bridge REST (code connu-bon)

Squelette validé (build net8.0 OK, silo démarré, ports pinés vérifiés par netstat).

## Bridge.csproj

- `Microsoft.NET.Sdk.Web`, `<TargetFramework>net8.0</TargetFramework>`.
- Références projet MARI : `MARI.Framework.Node`, `MARI.Framework.Builders`, `MARI.Framework.Core.Abstractions`, `MARI.Framework.Core`, `MARI.Framework.Node.Abstractions` (chemins relatifs vers le clone).
- `NuGet.config` local pointant vers `https://api.nuget.org/v3/index.json` (sinon restore NU1100).

## Program.cs — squelette

```csharp
// Définitions
var signalA = Signal.Create("rag-slow", "RagSlow");
var signalB = Signal.Create("cpu-high", "CpuHigh");

var door = Door.Create("door-a-b", "DoorAB")
               .Listen(signalA, signalB)
               .UseLogicalAggregator(LogicEnum.And, TimeSpan.FromSeconds(300))
               .Build();

var journalSequence = Sequence.Build("write-journal", "WriteJournal")
                              .RequiredInput<SignalMessage>()
                              .Use<IJournalWriterVGrain>()
                              .Configure("journal")
                              .Call((a, signal, ctx) => a.WriteAsync(signal, ctx)).Return
                              .Build();

var doorTrigger = Trigger.Door(door, "door-trigger", "DoorTrigger")
                         .AddTargetSequence(journalSequence)
                         .Build();

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://127.0.0.1:55553");

builder.Host.UseMARINode(b =>
{
    b.WizardConfig()
     .SetupCluster(_ => { })              // PAS NoCluster() : il force les ports par défaut
     .SetupNodeMemories(m => m.UseInMemory(StorageTypeEnum.All))
     .UseSignals()
     .ConfigureLogging(l => l.AddConsole())
     .AddInMemoryDefinitionProvider(m =>
     {
         m.SetupSignals(signalA, signalB)
          .SetupDoors(door)
          .SetupTriggers(doorTrigger)
          .SetupSequences(journalSequence);
     })
     .SetupNodeVGrains(cfg => cfg.Add<IJournalWriterVGrain, JournalWriterVGrain>());
});

// Pin des ports APRÈS (PostConfigure gagne sur l'auto-configuration)
builder.Host.ConfigureServices(s => s.PostConfigure<Orleans.Configuration.EndpointOptions>(o =>
{
    o.SiloPort = 55551;
    o.GatewayPort = 55552;
    o.AdvertisedIPAddress = System.Net.IPAddress.Loopback;
    o.SiloListeningEndpoint = null;
    o.GatewayListeningEndpoint = null;
}));

var app = builder.Build();

app.MapGet("/status", () => Results.Ok(new { status = "ok", signalsEmitted = ... }));

app.MapPost("/fire", (FireRequest req) =>
{
    var signalService = app.Services.GetRequiredService<ISignalService>();
    // data DOIT être null ou un struct (Fire rejette les reference types)
    signalService.Fire(req.fireId, (object?)null, CancellationToken.None);
    return Results.Ok(new { status = "signal emitted", fireId = req.fireId });
});

// Diagnostic : /diag subscribe par nom (non-OneWay) pour vérifier la résolution des définitions
//   SignalNotFoundException => définition absente ;
//   ArgumentException GetGrainId sur receiver non-grain => nom résolu.
app.Run();
```

## VGrain de side-effect (écriture journal)

```csharp
[VGrainIdFormat(IdFormatTypeEnum.String, FirstParameterTemplate = "journal")]
public interface IJournalWriterVGrain : IVGrain
{
    Task WriteAsync(SignalMessage signal, IExecutionContext<string> executionContext);
}

public sealed class JournalWriterVGrain : VGrainBase<IJournalWriterVGrain>, IJournalWriterVGrain, IGrainWithStringKey
{
    public Task WriteAsync(SignalMessage signal, IExecutionContext<string> ctx)
    {
        File.AppendAllText(@"C:/.../journal.log", $"[{DateTime.UtcNow:O}] door-fired fireId={signal.Uid}" + Environment.NewLine);
        return Task.CompletedTask;
    }
}
```

## Démarrage / arrêt / vérification

- Lancer : `dotnet run --no-build` en arrière-plan, stdout redirigé vers un log.
- Avant rebuild : `taskkill /F /PID <pid>` (la DLL bridge est verrouillée sinon : MSB3027/MSB3021).
- Vérifier : `netstat -ano | grep LISTENING | grep -E ":5555[123]"` ; `curl http://127.0.0.1:55553/status` ; `curl /diag` ; aucun port dans une plage réservée (netsh excludedportrange).
- Le log « Initializing silo on host ... at 127.0.0.1:PORT » et `SiloPort:` affichent le port RÉEL — c'est la preuve du pin, pas le code.

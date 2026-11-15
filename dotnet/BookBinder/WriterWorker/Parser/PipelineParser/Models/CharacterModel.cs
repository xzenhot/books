using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

internal sealed class CharacterModel
{
    // Canonical shape described by the framework.
    [JsonPropertyName("character_id")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? CharacterId { get; set; }

    [JsonPropertyName("full_name")]
    public string? FullName { get; set; }

    [JsonPropertyName("role")]
    public string? Role { get; set; }

    // Usually a text description, but some plans store an object such as {age, sex, caste}.
    [JsonPropertyName("identity")]
    public JsonElement? Identity { get; set; }

    [JsonPropertyName("psychological_depth")]
    public string? PsychologicalDepth { get; set; }

    // Shorter shape used by older novel plans.
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("arc")]
    public string? Arc { get; set; }

    [JsonIgnore]
    public string? ResolvedId => CharacterId ?? Id;

    [JsonIgnore]
    public string? ResolvedName => FullName ?? Name;

    [JsonIgnore]
    public string? ResolvedDepth => PsychologicalDepth ?? Arc;

    /// <summary>Identity as displayable text; objects come back as their raw JSON.</summary>
    [JsonIgnore]
    public string? IdentityText
    {
        get
        {
            if (Identity is not { } identity)
            {
                return null;
            }

            return identity.ValueKind switch
            {
                JsonValueKind.String => identity.GetString(),
                JsonValueKind.Undefined or JsonValueKind.Null => null,
                _ => identity.GetRawText(),
            };
        }
    }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

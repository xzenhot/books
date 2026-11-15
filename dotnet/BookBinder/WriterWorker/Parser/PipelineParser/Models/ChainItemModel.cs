using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// One entry of <c>filter_chain</c> or <c>quality_chain</c>. Plans store these either as plain
/// names ("workshop") or as objects (<c>{sl, filter, autorun, reference}</c>).
/// </summary>
internal sealed class ChainItemModel
{
    /// <summary>Name from the plain-string form; null when the plan used the object form.</summary>
    public string? Name { get; set; }

    public int? Sl { get; set; }

    public string? Filter { get; set; }

    public string? Quality { get; set; }

    public bool? Autorun { get; set; }

    public string? Reference { get; set; }

    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }

    public string? DisplayName => Name ?? Filter ?? Quality;

    internal bool IsPlainName =>
        Name is not null && Filter is null && Quality is null && Sl is null && Autorun is null && Reference is null;
}

/// <summary>Keeps the original shape of each chain entry so plans round-trip unchanged.</summary>
internal sealed class ChainItemListConverter : JsonConverter<List<ChainItemModel>>
{
    public override List<ChainItemModel> Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType != JsonTokenType.StartArray)
        {
            throw new JsonException($"Expected an array of chain items but found {reader.TokenType}.");
        }

        var items = new List<ChainItemModel>();
        while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
        {
            items.Add(reader.TokenType switch
            {
                JsonTokenType.String => new ChainItemModel { Name = reader.GetString() },
                JsonTokenType.StartObject => ReadObject(ref reader),
                _ => throw new JsonException($"Unexpected chain item token {reader.TokenType}."),
            });
        }

        return items;
    }

    public override void Write(Utf8JsonWriter writer, List<ChainItemModel> value, JsonSerializerOptions options)
    {
        writer.WriteStartArray();
        foreach (var item in value)
        {
            if (item.IsPlainName)
            {
                writer.WriteStringValue(item.Name);
                continue;
            }

            writer.WriteStartObject();
            if (item.Sl is { } sl)
            {
                writer.WriteNumber("sl", sl);
            }

            if (item.Filter is not null)
            {
                writer.WriteString("filter", item.Filter);
            }

            if (item.Quality is not null)
            {
                writer.WriteString("quality", item.Quality);
            }

            if (item.Autorun is { } autorun)
            {
                writer.WriteBoolean("autorun", autorun);
            }

            if (item.Reference is not null)
            {
                writer.WriteString("reference", item.Reference);
            }

            if (item.AdditionalProperties is { } extras)
            {
                foreach (var (key, element) in extras)
                {
                    writer.WritePropertyName(key);
                    element.WriteTo(writer);
                }
            }

            writer.WriteEndObject();
        }

        writer.WriteEndArray();
    }

    private static ChainItemModel ReadObject(ref Utf8JsonReader reader)
    {
        var item = new ChainItemModel();
        while (reader.Read() && reader.TokenType != JsonTokenType.EndObject)
        {
            if (reader.TokenType != JsonTokenType.PropertyName)
            {
                throw new JsonException($"Unexpected token {reader.TokenType} in a chain item.");
            }

            var name = reader.GetString();
            reader.Read();
            switch (name)
            {
                case "sl":
                    item.Sl = reader.TokenType == JsonTokenType.Number && reader.TryGetInt32(out var sl) ? sl : null;
                    break;
                case "filter":
                    item.Filter = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                    break;
                case "quality":
                    item.Quality = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                    break;
                case "autorun":
                    item.Autorun = reader.TokenType switch
                    {
                        JsonTokenType.True => true,
                        JsonTokenType.False => false,
                        _ => null,
                    };
                    break;
                case "reference":
                    item.Reference = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                    break;
                default:
                    item.AdditionalProperties ??= [];
                    item.AdditionalProperties[name ?? string.Empty] = JsonElement.ParseValue(ref reader);
                    break;
            }
        }

        return item;
    }
}

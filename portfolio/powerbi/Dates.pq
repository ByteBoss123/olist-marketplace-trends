let
    Source = Csv.Document(File.Contents(DataFolder & "Dates.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"date_key", type date}, {"month", type text}, {"year", Int64.Type}}, "en-US")
in
    Typed

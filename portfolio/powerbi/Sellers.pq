let
    Source = Csv.Document(File.Contents(DataFolder & "Sellers.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"seller_id", type text}, {"seller_state", type text}}, "en-US")
in
    Typed

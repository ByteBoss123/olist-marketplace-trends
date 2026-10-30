let
    Source = Csv.Document(File.Contents(DataFolder & "Orders.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"order_id", type text}, {"date_key", type date}, {"order_status", type text}, {"on_time", Int64.Type}, {"review_score", Int64.Type}}, "en-US")
in
    Typed

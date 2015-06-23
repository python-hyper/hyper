(import hyper json)

(defn http2bin [path]
  (with [[conn (hyper.HTTPConnection "http2bin.org")]]
    (.request conn "GET" path)
    (-> (.get_response conn) (.read) (json.loads))))

(-> (http2bin "/ip") (get "origin") (print))

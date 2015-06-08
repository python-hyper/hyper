; Reports the users mentioned in the initially loaded tweets on a user's
; Twitter page.

(import hyper bs4)

(setv results {})

; Get hold of a stream ID for the data for a single page.
(defn request-page [conn path]
  (.request conn "GET" path))

; Read the stream to exhaustion.
(defn get-page-data [conn req-id]
  (-> (.get_response conn req-id) (.read)))

; Yield all at-reply elements from the html.
(defn at-replies [html]
  (let [[soup (bs4.BeautifulSoup html)]]
    (apply .find_all [soup] {"class_" "twitter-atreply"})))

(defn get-refs [replies]
  (list-comp (.get reply "href") [reply replies]))

(defn mentions [html]
  (for [ref (remove none? (get-refs (at-replies html)))]
    (-> (.lstrip ref "/") (yield))))

; Simple test: print the people referenced on the most recent tweets page.
(defn main []
  (with [[conn (hyper.HTTPConnection "twitter.com" 443)]]
    (let [[req-id (request-page conn "/Lukasaoz")]]
      (for [mention (mentions (get-page-data conn req-id))]
        (print mention)))))

(main)

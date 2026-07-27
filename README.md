# Claude Ai shared chats

## What's this

Whenever you click share on a conversation on claude, chatgpt, grok etc. to a friend/ colleague, it does so by generating a public url. This url can be accessed by anyone. 

This program scrapes such indexed links (it uses duckduckgo, with google as fallback), and extracts the text and stores them. 

---

# Setup

```bash
pip install -r requirements.txt
```
 
Requirements: `curl_cffi` (to fetch share pages), `ddgs` (for link discovery), and `firebase-admin` (only needed if you use the Firestore upload).
 
Alternatively, you can just visit my website (https://aisharedchats.netlify.app/)[https://aisharedchats.netlify.app/]. It updates daily with any new claude convos it finds

# Limitations

- This only works for convos which have been shared. Private convos cannot be accessed. Shared convos are public, so treat it similar to how you would treat any public content on the internet
- Not all shared convos can be accessed either. This just gets the ones which have been indexed by duckduckgo or google, which is a rather small number compared to the overall amount

#Future scope

May look into adding other sites like grok and chatgpt

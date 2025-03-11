import requests

def transliterate(english_text):
    url = "https://inputtools.google.com/request"
    params = {
        'text': english_text,
        'itc': 'ta-t-i0-und',
        'num': 13,
        'cp': 0,
        'cs': 0,
        'ie': 'utf-8',
        'oe': 'utf-8'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 

        data = response.json()
        # print(data)
        if data[0] == 'SUCCESS':
            return 0, data[1][0][1][0]
        else:
            return 1, ''
    except requests.exceptions.RequestException as e:
        print(f"Error requesting transliteration: {e}")
        return 1, ''

if __name__ == "__main__":
    text = "Enna panra? saptiya? Amma appa nalla irukangala? pork kaalathil irukku"
    print(text)
    print(transliterate(text)[1])

# Enna panra? saptiya? Amma appa nalla irukangala? pork kaalathil irukku
# என்ன பண்ற? சாப்டியா? அம்மா அப்பா நல்லா இருக்காங்களா? போர்க் காலத்தில் இருக்கு
//! Ave Imperator, on the `caeser-cipher` crate documentation
//!
//! This crates provides the tools to be able to __encrypt__ and
//! __decrypt__ messages using the [Caesar cipher](https://en.wikipedia.org/wiki/Caesar_cipher).
//!
//! To summarize, in this encryption scheme, we have an alphabet in which the clear text is in.
//! And to encrypt a clear text we shift the alphabet by a number.
//!
use crate::alphabets::Alphabet;

pub mod alphabets;

pub struct Shift(pub usize);


#[derive(Debug, Eq, PartialEq)]
pub struct CharacterNotInAlphabet(pub char);


/// Struct that encrypts and decrypts message.
///
/// An engine is tied to an [Alphabet] and will only be able to
/// [encrypt] / [decrypt] messages that are in the same `Alphabet`.
///
///
/// # Examples
///
/// Correctly using the same Alphabet:
/// ```
/// use caesar_cipher::alphabets::IncompleteAscii;
/// use caesar_cipher::{CaesarEngine, Shift, ClearText};
///
/// let message = ClearText::<IncompleteAscii>::try_new("Ave Imperator, morituri te salutant").unwrap();
///
/// let engine = CaesarEngine::<IncompleteAscii>::new(Shift(17));
///
/// let encrypted_message = engine.encrypt(&message);
/// let decrypted_message = engine.decrypt(&encrypted_message);
///
/// assert_eq!(decrypted_message, message);
/// ```
///
/// Trying to mix [Alphabet]s will create a compile error
/// ```compile_fail
/// use caesar_cipher::alphabets::{AsciiLowerCaseAlphabet, IncompleteAscii};
/// use caesar_cipher::{CaesarEngine, Shift, ClearText};
///
/// let message = ClearText::<IncompleteAscii>::try_new("Ave Imperator, morituri te salutant").unwrap();
///
/// let engine = CaesarEngine::<AsciiLowerCaseAlphabet>::new(Shift(17));
///
/// // This line make compilation fail
/// let encrypted_message = engine.encrypt(&message);
/// ```
///
/// [encrypt]: Self::encrypt
/// [decrypt]: Self::decrypt
pub struct CaesarEngine<A: Alphabet> {
    _marker: std::marker::PhantomData<A>,
    shifted_alphabet: Vec<char>,
}



impl<A: Alphabet> CaesarEngine<A> {
    /// Creates a new
    pub fn new(shift: Shift) -> Self {
        let mut shifted_alphabet = A::letters().to_vec();
        shifted_alphabet.rotate_left(shift.0);

        Self {
            _marker: Default::default(),
            shifted_alphabet,
        }
    }

    pub fn encrypt(&self, clear_message: &ClearText<A>) -> CipherText<A> {
        let mut encrypted_message = String::with_capacity(clear_message.message.len());
        let alphabet = A::letters();
        for letter in clear_message.message.chars() {
            let letter_index = alphabet.iter().position(|l| l == &letter).unwrap();
            encrypted_message.push(self.shifted_alphabet[letter_index]);
        }

        CipherText {
            _marker: Default::default(),
            cipher: encrypted_message,
        }
    }

    pub fn decrypt(&self, cipher_message: &CipherText<A>) -> ClearText<A> {
        let mut clear_message = String::with_capacity(cipher_message.cipher.len());
        let alphabet = A::letters();
        for letter in cipher_message.cipher.chars() {
            let letter_index = self
                .shifted_alphabet
                .iter()
                .position(|l| &letter == l)
                .unwrap();
            clear_message.push(alphabet[letter_index]);
        }

        ClearText {
            _marker: Default::default(),
            message: clear_message,
        }
    }
}

/// A Clear text is a non encrypted message
///
/// As with all other types in the library, a `ClearText` message
/// is tied to an [Alphabet].
///
///
/// # Examples
///
/// Cleartext using string message that fits in the alphabet
/// ```
/// use caesar_cipher::alphabets::AsciiLowerCaseAlphabet;
/// use caesar_cipher::ClearText;
/// let clear_text = ClearText::<AsciiLowerCaseAlphabet>::try_new("message");
/// assert!(clear_text.is_ok());
/// ```
/// Cleartext using string message that __does not__ fit in the alphabet
/// ```
/// use caesar_cipher::alphabets::AsciiLowerCaseAlphabet;
/// use caesar_cipher::{CharacterNotInAlphabet, ClearText};
/// let clear_text = ClearText::<AsciiLowerCaseAlphabet>::try_new("mEssage");
/// assert!(clear_text.is_err());
/// assert_eq!(clear_text, Err(CharacterNotInAlphabet('E')));
/// ```
///
#[derive(Debug, Eq, PartialEq)]
pub struct ClearText<A> {
    _marker: std::marker::PhantomData<A>,
    message: String,
}



impl<A: Alphabet> ClearText<A> {
    pub fn try_new<T: ToString>(message: T) -> Result<Self, CharacterNotInAlphabet> {
        let message = message.to_string();
        let alphabet_letters = A::letters();
        let pos = message
            .chars()
            .position(|ref c| !alphabet_letters.contains(c));
        if let Some(p) = pos {
            Err(CharacterNotInAlphabet(message.chars().nth(p).unwrap()))
        } else {
            Ok(Self {
                _marker: Default::default(),
                message,
            })
        }
    }
}

impl<A> AsRef<String> for ClearText<A> {
    fn as_ref(&self) -> &String {
        &self.message
    }
}

impl<A: Alphabet> PartialEq<str> for ClearText<A> {
    fn eq(&self, other: &str) -> bool {
        &self.message == other
    }
}

#[derive(Debug, Eq, PartialEq)]
pub struct CipherText<A: Alphabet> {
    _marker: std::marker::PhantomData<A>,
    cipher: String,
}

impl<A: Alphabet> PartialEq<str> for CipherText<A> {
    fn eq(&self, other: &str) -> bool {
        &self.cipher == other
    }
}



#[cfg(test)]
mod tests {
    use super::*;
    use crate::alphabets::{AsciiLowerCaseAlphabet, IncompleteAscii};

    #[test]
    fn test_simple() {
        let engine = CaesarEngine::<AsciiLowerCaseAlphabet>::new(Shift(3));
        let message = ClearText::<AsciiLowerCaseAlphabet>::try_new("abcd").unwrap();

        let encrypted_message = engine.encrypt(&message);
        assert_eq!(&encrypted_message, "defg");

        let decrypted_message = engine.decrypt(&encrypted_message);
        assert_eq!(decrypted_message, message);
    }

    #[test]
    fn hello_world() {
        let engine = CaesarEngine::<AsciiLowerCaseAlphabet>::new(Shift(3));
        let message = ClearText::<AsciiLowerCaseAlphabet>::try_new("helloworld").unwrap();

        let encrypted_message = engine.encrypt(&message);
        assert_eq!(&encrypted_message, "khoorzruog");

        let decrypted_message = engine.decrypt(&encrypted_message);
        assert_eq!(decrypted_message, message);
    }

    #[test]
    fn test_letter_not_in_alphabet() {
        let result = ClearText::<AsciiLowerCaseAlphabet>::try_new(String::from("hello world"));
        assert_eq!(result, Err(CharacterNotInAlphabet(' ')));
    }

    #[test]
    fn complete_sentence() {
        let message = ClearText::<IncompleteAscii>::try_new("Concrete is based on the Learning With Errors (LWE) and the Ring Learning With Errors (RLWE) problems,\
         which are well studied cryptographic hardness assumptions believed to be secure even against quantum computers.").unwrap();

        let engine = CaesarEngine::<IncompleteAscii>::new(Shift(3));

        let encrypted_message = engine.encrypt(&message);

        let decrypted_message = engine.decrypt(&encrypted_message);
        assert_eq!(decrypted_message, message);
    }
}

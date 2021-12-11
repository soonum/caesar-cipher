use std::fmt::Debug;

pub trait Alphabet: Debug {
    /// All the letters and symbols that composes the alphabet
    fn letters() -> &'static [char];
}

/// This alphabet contains only lowercase ascii letters (and no symbols)
#[derive(Debug, Eq, PartialEq)]
pub struct AsciiLowerCaseAlphabet;

impl Alphabet for AsciiLowerCaseAlphabet {
    fn letters() -> &'static [char] {
        const CAESAR_ALPHABET: [char; 26] = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
            'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        ];

        // Commentaire 1
        &CAESAR_ALPHABET
    }
}

#[derive(Debug, Eq, PartialEq)]
pub struct IncompleteAscii;

impl Alphabet for IncompleteAscii {
    fn letters() -> &'static [char] {
        const INCOMPLETE_ASCII: [char; 60] = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
            'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
            'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
            'Z', ',', ' ', '?', '!', '\'', '(', ')', '.',
        ];

        &INCOMPLETE_ASCII
    }
}

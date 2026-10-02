
export const isValidEmail = (email) => {
    // Check if email has any uppercase letters
    if (email !== email.toLowerCase()) {
        return false;
    }
    const emailRegex = /^[a-z][a-z0-9._%+-]*@[a-z0-9.-]+\.[a-z]{2,}$/;
    return emailRegex.test(email);
};

export const isValidPassword = (password) => {

    if (password.length < 9) return false;
    if (!/[A-Z]/.test(password)) return false;
    if (!/[a-z]/.test(password)) return false;
    return true;
};

export const getPasswordValidationMessage = () => {
    return "Password must be at least 9 characters long and contain both uppercase and lowercase letters. Numbers and special characters are allowed.";
};

export const getEmailValidationMessage = () => {
    return "Email must be in lowercase, not start with a number, and be in a valid format (e.g., username@domain.com).";
};
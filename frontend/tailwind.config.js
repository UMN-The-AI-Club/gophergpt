/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'maroon': '#7A0019',
                'maroon-dark': '#5e0014',
                'maroon-mid': '#8c0a20',
                'gold': '#FFCC33',
                'gold-dark': '#d99a26',
                'app-bg': '#1a1718',
                'sidebar-bg': '#211e1f',
                'card': '#252122',
                'card-hover': '#2c2728',
                'dock-bg': '#1c1a1b',
                'input-bg': '#2c2829',
                'dark-gray': '#1a1718',
                'message-bg': '#252122',
            },
            animation: {
                'fade-in': 'fadeIn 0.7s ease-in-out',
                'fade-out': 'fadeOut 0.7s ease-in-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                fadeOut: {
                    '0%': { opacity: '1' },
                    '100%': { opacity: '0' },
                },
            },
        },
    },
    plugins: [],
}

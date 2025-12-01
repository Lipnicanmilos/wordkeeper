## Features Implemented
- Repeat buttons on dashboard for each category and knowledge level
- Repeat page with flashcard-style interface
- Support for different knowledge levels (Don't Know, Learning, Know)
- Bilingual support (English/Slovak)
- Responsive design matching the app's style
- Session-based authentication
- Progress tracking during repeat sessions
- **Audio playback for words and translations**
- **Auto-play mode with 4-second intervals (2s word + 2s translation)**

## How to Use
1. Go to the dashboard
2. For any category, click on the "🔄 [Level]" buttons to repeat words of that knowledge level
3. The repeat page will show flashcards for review
4. Use the interface to go through words and improve knowledge levels
5. **Click "Auto Play" for automatic audio playback of all words**
6. **Each word plays audio for 2 seconds, then translation plays for 2 seconds**

## Technical Details
- Uses existing `/api/v1/words/test/start` endpoint for fetching words
- Repeat page is similar to test page but focused on review rather than testing
- Maintains session authentication and user-specific data
- Integrates with existing word management system
- Fixed authentication issues with proper credentials handling
- **Added Web Speech API for text-to-speech functionality**
- **Auto-play mode with timed intervals for immersive learning**

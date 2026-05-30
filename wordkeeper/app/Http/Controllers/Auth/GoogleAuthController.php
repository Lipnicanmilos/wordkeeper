<?php
public function redirectToGoogle()
{
    return Socialite::driver('google')->redirect();
}

public function handleGoogleCallback()
{
    try {
        $googleUser = Socialite::driver('google')->user();
        
        // Nájdeme alebo vytvoríme používateľa
        $user = User::where('email', $googleUser->email)->first();
        
        if (!$user) {
            // Nová registrácia cez Google
            $user = User::createFromGoogle($googleUser);
            
            // Môžeme tu pridať welcome email alebo inú logiku
        } else {
            // Aktualizujeme Google ID ak chýba
            if (!$user->google_id) {
                $user->update(['google_id' => $googleUser->id]);
            }
        }
        
        // Prihlásime používateľa
        Auth::login($user, true);
        
        // Vygenerujeme token pre frontend
        $token = $user->createToken('google-auth')->plainTextToken;
        
        // Presmerujeme na frontend s tokenom
        return redirect(env('FRONTEND_URL') . '/auth/callback?token=' . $token . '&new_user=' . ($user->wasRecentlyCreated ? '1' : '0'));
        
    } catch (\Exception $e) {
        return redirect('/login')->with('error', 'Google authentication failed');
    }
}
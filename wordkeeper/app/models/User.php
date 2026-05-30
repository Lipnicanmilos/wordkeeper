<?php
public function createFromGoogle($googleUser)
{
    return $this->create([
        'name' => $googleUser->name,
        'email' => $googleUser->email,
        'google_id' => $googleUser->id,
        'avatar' => $googleUser->avatar,
        'email_verified_at' => now(), // Google email je overený
        'password' => null, // Používateľ nebude mať password
    ]);
}
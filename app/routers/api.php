<?php
Route::middleware('auth:sanctum')->group(function () {
    Route::get('/users/me', [UserController::class, 'getCurrentUser']);
});
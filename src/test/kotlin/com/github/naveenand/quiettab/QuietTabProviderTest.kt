package com.github.naveenand.quiettab

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

// Fix 1: files that may hold secrets are never sent to the model or written to the log
class QuietTabProviderTest {

    @Test
    fun secretFilesAreSkipped() {
        for (name in listOf(".env", ".env.local", "server.pem", "id_rsa", "aws_credentials.json", "my_secret.py", "keystore.jks")) {
            assertTrue("should skip $name", QuietTabProvider.isSensitive(name))
        }
    }

    @Test
    fun normalFilesAreNotSkipped() {
        for (name in listOf("demo.py", "app.py", "Main.java", "environment.py", "keyboard.kt", "README.md")) {
            assertFalse("should NOT skip $name", QuietTabProvider.isSensitive(name))
        }
    }
}

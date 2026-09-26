package ai.astrovox

import android.app.Application
import androidx.room.Room
import ai.astrovox.data.local.AppDatabase

class AstrovoxAIApplication : Application() {
    lateinit var database: AppDatabase
        private set

    override fun onCreate() {
        super.onCreate()
        database = Room.databaseBuilder(
            applicationContext,
            AppDatabase::class.java,
            "astrovox_database"
        ).fallbackToDestructiveMigration().build()
    }
}

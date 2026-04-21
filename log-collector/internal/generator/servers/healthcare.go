package servers

import (
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"

	"migrate/internal/generator"
)

// HealthcareServer generates healthcare logs
type HealthcareServer struct {
	*generator.BaseServer
	chainProbabilities map[string]float64
	chainTemplates     []string
}

// NewHealthcareServer creates a new healthcare server
func NewHealthcareServer() *HealthcareServer {
	// Get the absolute path for patterns
	patternsFile := "healthcare_patterns.json"
	if _, err := os.Stat(patternsFile); os.IsNotExist(err) {
		patternsFile = filepath.Join("..", "patterns", "healthcare_patterns.json")
	}
	
	hs := &HealthcareServer{
		BaseServer: generator.NewBaseServer("healthcare", "healthcare_server.log", patternsFile),
		chainProbabilities: map[string]float64{
			"step_update":   0.4,
			"screen_toggle": 0.1,
			"report":        0.3,
			"sync_event":    0.05,
			"db_error":      0.02,
		},
		chainTemplates: []string{
			"onStandStepChanged",
			"setTodayTotalDetailSteps",
			"calculateCaloriesWithCache",
			"REPORT",
			"onExtend",
		},
	}
	
	// Initialize healthcare-specific state
	hs.State["step_count"] = 3579
	hs.State["total_calories"] = 126775
	hs.State["altitude"] = 240
	hs.State["patient_id"] = 30002312
	hs.State["screen_on"] = true
	hs.State["sync_counter"] = 0
	
	hs.MaxLogs = 20
	
	fmt.Printf("   🏥 Healthcare state: steps=%v, calories=%v\n", 
		hs.State["step_count"], hs.State["total_calories"])
	
	return hs
}

// GenerateLogLine generates healthcare-specific log
func (hs *HealthcareServer) GenerateLogLine() map[string]interface{} {
	rand := rand.Float64()
	
	if rand < hs.chainProbabilities["step_update"] {
		hs.generateStepChain()
		return map[string]interface{}{"skip": true}
	} else if rand < hs.chainProbabilities["step_update"]+hs.chainProbabilities["screen_toggle"] {
		return hs.generateScreenEvent()
	} else if rand < hs.chainProbabilities["step_update"]+hs.chainProbabilities["screen_toggle"]+hs.chainProbabilities["report"] {
		return hs.generateReport()
	} else if rand < hs.chainProbabilities["step_update"]+hs.chainProbabilities["screen_toggle"]+hs.chainProbabilities["report"]+hs.chainProbabilities["sync_event"] {
		return hs.generateSyncEvent()
	} else if rand < hs.chainProbabilities["step_update"]+hs.chainProbabilities["screen_toggle"]+hs.chainProbabilities["report"]+hs.chainProbabilities["sync_event"]+hs.chainProbabilities["db_error"] {
		return hs.generateDBError()
	}
	
	return hs.generateRegularLog()
}

// generateStepChain generates a chain of step-related events
func (hs *HealthcareServer) generateStepChain() {
	stepIncrement := rand.Intn(3) + 1
	stepCount := hs.State["step_count"].(int) + stepIncrement
	hs.State["step_count"] = stepCount
	
	calories := hs.State["total_calories"].(int) + (stepIncrement * 17)
	hs.State["total_calories"] = calories
	
	patientID := hs.State["patient_id"].(int)
	
	// Log 1: Step changed
	hs.WriteLog(map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_LSC",
		"user_id":   fmt.Sprintf("%d", patientID),
		"message":   fmt.Sprintf("onStandStepChanged %d", stepCount),
	})
	
	// Log 2: Update storage
	hs.WriteLog(map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_SPUtils",
		"user_id":   fmt.Sprintf("%d", patientID),
		"message":   fmt.Sprintf("setTodayTotalDetailSteps=%d", stepCount),
	})
	
	// Log 3: Recalculate calories
	hs.WriteLog(map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_ExtSDM",
		"user_id":   fmt.Sprintf("%d", patientID),
		"message":   fmt.Sprintf("calculateCaloriesWithCache totalCalories=%d", calories),
	})
	
	// Log 4: Generate report
	distance := rand.Intn(1000) + 5000
	altitude := hs.State["altitude"].(int)
	hs.WriteLog(map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_StandReportReceiver",
		"user_id":   fmt.Sprintf("%d", patientID),
		"message":   fmt.Sprintf("REPORT : %d %d %d %d", stepCount, distance, calories, altitude),
	})
}

// generateScreenEvent toggles screen state
func (hs *HealthcareServer) generateScreenEvent() map[string]interface{} {
	screenOn := hs.State["screen_on"].(bool)
	hs.State["screen_on"] = !screenOn
	
	action := "SCREEN_OFF"
	if !screenOn {
		action = "SCREEN_ON"
	}
	
	return map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_StandReportReceiver",
		"user_id":   fmt.Sprintf("%d", hs.State["patient_id"].(int)),
		"message":   fmt.Sprintf("onReceive action: android.intent.action.%s", action),
	}
}

// generateReport generates a report log
func (hs *HealthcareServer) generateReport() map[string]interface{} {
	stepCount := hs.State["step_count"].(int)
	calories := hs.State["total_calories"].(int)
	altitude := hs.State["altitude"].(int)
	distance := rand.Intn(1000) + 5000
	
	return map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "Step_StandReportReceiver",
		"user_id":   fmt.Sprintf("%d", hs.State["patient_id"].(int)),
		"message":   fmt.Sprintf("REPORT : %d %d %d %d", stepCount, distance, calories, altitude),
	}
}

// generateSyncEvent generates sync-related events
func (hs *HealthcareServer) generateSyncEvent() map[string]interface{} {
	syncCounter := hs.State["sync_counter"].(int)
	hs.State["sync_counter"] = syncCounter + 1
	
	syncMessages := []string{
		"startTimer start autoSync",
		"startSync hiSyncOption = HiSyncOption{syncAction=1, syncMethod=2, syncScope=0, syncDataType=20000, syncModel=2, pushAction=0},app = 1 who = 1",
		"needAutoSync autoSyncSwitch is open",
		"initDataPrivacy the dataPrivacy switch is open, start push health data!",
		"initDataPrivacy the dataPrivacy is true",
		"initUserPrivacy the userPrivacy switch is open, start push user data!",
		"initUserPrivacy the userPrivacy is true",
		"ifCanSync not! no cloud version",
		"sendSyncFailedBroadcast",
	}
	
	return map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": "HiH_HiSyncControl",
		"user_id":   fmt.Sprintf("%d", hs.State["patient_id"].(int)),
		"message":   syncMessages[rand.Intn(len(syncMessages))],
	}
}

// generateDBError generates database error events
func (hs *HealthcareServer) generateDBError() map[string]interface{} {
	errorMessages := []string{
		fmt.Sprintf("saveHealthDetailData() saveOneDetailData fail hiHealthData = 1513958400000,type = 40003"),
		"insertHiHealthData() bulkSaveDetailHiHealthData fail errorCode = 4,errorMessage = ERR_DATA_INSERT",
		fmt.Sprintf("step count inconsistency detected: expected %d got %d", 
			hs.State["step_count"].(int), hs.State["step_count"].(int)+rand.Intn(3)+1),
		fmt.Sprintf("slow database query detected: took %dms", rand.Intn(10000)+5000),
	}
	
	components := []string{"HiH_HiHealthDataInsertStore", "HiH_HiHealthBinder", "HiH_HiSyncControl"}
	
	return map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": components[rand.Intn(len(components))],
		"user_id":   fmt.Sprintf("%d", hs.State["patient_id"].(int)),
		"message":   errorMessages[rand.Intn(len(errorMessages))],
	}
}

// generateRegularLog generates a regular log using templates
func (hs *HealthcareServer) generateRegularLog() map[string]interface{} {
	templates := hs.Patterns.Templates.ByFrequency
	
	// Filter out chain templates
	availableTemplates := make([]string, 0)
	for template := range templates {
		isChainTemplate := false
		for _, chainTemplate := range hs.chainTemplates {
			if strings.Contains(template, chainTemplate) {
				isChainTemplate = true
				break
			}
		}
		if !isChainTemplate {
			availableTemplates = append(availableTemplates, template)
		}
	}
	
	var message string
	if len(availableTemplates) > 0 {
		template := availableTemplates[rand.Intn(len(availableTemplates))]
		message = hs.FillTemplate(template)
	} else {
		realMessages := []string{
			fmt.Sprintf("getTodayTotalDetailSteps = 1514038440000##%d##548365##8661##%d##%d",
				hs.State["step_count"].(int), rand.Intn(4000)+12000, rand.Intn(50000)+27100000),
			fmt.Sprintf("saveStatData() type =40002,time = 1513958400000,statClient = 2,who is 1"),
			fmt.Sprintf("new date =20171223, type=40002,%d.0,old=%d.0",
				hs.State["step_count"].(int), hs.State["step_count"].(int)-rand.Intn(20)+10),
			"getBinderPackageName packageName = com.huawei.health",
			"getAppContext() isAppValid health or wear, packageName = com.huawei.health",
		}
		message = realMessages[rand.Intn(len(realMessages))]
	}
	
	return map[string]interface{}{
		"timestamp": hs.GenerateTimestamp(),
		"component": hs.GetRandomComponent(),
		"user_id":   fmt.Sprintf("%d", hs.State["patient_id"].(int)),
		"message":   message,
	}
}

backend_ctrl_block_decode --> DecodeStage --> ut_backend/ctrl_block/decode
frontend_bpu_ittage --> ITTage --> ut_frontend/bpu/ittage
frontend_bpu_tagesc --> Tage_SC --> ut_frontend/bpu/tagesc
frontend_ifu_f3predecoder --> F3Predecoder --> ut_frontend/ifu/f3predecoder
frontend_ifu_frontend_trigger --> FrontendTrigger --> ut_frontend/ifu/frontend_trigger
frontend_ifu_pred_checker --> PredChecker --> ut_frontend/ifu/pred_checker
frontend_ifu_predecode --> PreDecode --> ut_frontend/ifu/predecode
frontend_ifu_rvc_expander --> RVCExpander --> ut_frontend/ifu/rvc_expander
frontend_ifu_top --> NewIFU --> 
frontend_itlb --> TLB --> ut_frontend/itlb/classical_version
frontend_itlb --> TLB --> ut_frontend/itlb/toffee_version
frontend_tlb_fa --> TLBFA --> ut_frontend/itlb/submodules/TLBFA
frontend_tlb_nonblock --> TLBNonBlock --> ut_frontend/itlb/submodules/TLBNonBlock
frontend_tlb_storage_wrapper --> TlbStorageWrapper --> ut_frontend/itlb/submodules/TlbStorageWrapper
frontend_tlbuffer --> TLBuffer --> ut_frontend/itlb/submodules/TLBuffer